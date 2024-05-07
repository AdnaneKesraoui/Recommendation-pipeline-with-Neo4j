import json
import re
from uuid import uuid4

from flask import Flask, jsonify, request
from kafka import KafkaProducer
from neo4j import GraphDatabase

app = Flask(__name__)

uri = "neo4j://localhost:7687"
user = "neo4j"
password = "twittertwitter"

driver = GraphDatabase.driver(uri, auth=(user, password))


# Initialize Kafka Producer
producer = KafkaProducer(bootstrap_servers=['localhost:9092'],
                         value_serializer=lambda v: json.dumps(v).encode('utf-8'))

def send_tweet_for_analysis(tweet_id, tweet_text):
    message = {'tweet_id': tweet_id, 'text': tweet_text}
    producer.send('tweet_analysis', value=message)
    producer.flush()   

def get_db_session():
    return driver.session()

#fetch all users data
@app.route('/users_data')
def fetch_data():
    query = "MATCH (n) RETURN n LIMIT 5"

    with get_db_session() as session:
        results = session.run(query)
        data = [record["n"]._properties for record in results]
        return jsonify(data)
    


#this is how the connected user is going to try and post tweets
@app.route('/create_tweet', methods=['POST'])
def create_tweet():
    data = request.json
    tweet_text = data.get('text')
    poster_id = data.get('poster_id')
    name = data.get('name')
    
    if not tweet_text or not poster_id or not name:
        return jsonify({"error": "Tweet text, poster ID, or name is missing"}), 400

    hashtags = re.findall(r'#(\w+)', tweet_text)
    tweet_id = str(uuid4())
    
    send_tweet_for_analysis(tweet_id, tweet_text)

    
    query = """
    MERGE (me:Me {id: $poster_id})
    ON CREATE SET me.name = $name
    ON MATCH SET me.name = $name
    CREATE (tweet:Tweet {id: $tweet_id, text: $tweet_text, createdAt: datetime()})
    CREATE (me)-[:POSTS]->(tweet)
    """
    
    parameters = {'poster_id': poster_id, 'name': name, 'tweet_id': tweet_id, 'tweet_text': tweet_text}
    with get_db_session() as session:
        session.run(query, parameters)
    
    for hashtag in hashtags:
        query_hashtag = """
        MERGE (hashtag:Hashtag {name: $hashtag})
        WITH hashtag
        MATCH (tweet:Tweet {id: $tweet_id})
        MERGE (tweet)-[:TAGS]->(hashtag)
        """
        with get_db_session() as session:
            session.run(query_hashtag, {'hashtag': hashtag, 'tweet_id': tweet_id})
    
    return jsonify({"message": "Tweet created and linked to hashtags successfully", "tweet_id": tweet_id, "name": name}), 201



#get other users recommendations based on the tweets that the user has posted   
@app.route('/get_recommendations', methods=['GET'])
def related_users_shared_hashtags():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    fetch_hashtags_query = """
    MATCH (me:Me {id: $user_id})-[:POSTS]->(tweet:Tweet)-[:TAGS]->(hashtag:Hashtag)
    RETURN DISTINCT hashtag.name AS hashtag
    """
    
    with get_db_session() as session:
        results = session.run(fetch_hashtags_query, user_id=user_id)
        hashtags = [record["hashtag"] for record in results]

    if not hashtags:
        return jsonify({"user_id": user_id, "message": "No hashtags found for this user", "related_users": []})

    find_users_query = """
    MATCH (tweet:Tweet)-[:TAGS]->(hashtag:Hashtag)
    WHERE hashtag.name IN $hashtags
    MATCH (user:Me)-[:POSTS]->(tweet)
    WHERE user.id <> $user_id
    RETURN DISTINCT user.id AS userId, user.name AS userName
    """

    users = []
    with get_db_session() as session:
        results = session.run(find_users_query, hashtags=hashtags, user_id=user_id)
        users = [{"user_id": record["userId"], "user_name": record["userName"]} for record in results]

    return jsonify({"user_id": user_id, "hashtags": hashtags, "related_users": users})



        
if __name__ == '__main__':
    app.run(debug=True, port=5001)

