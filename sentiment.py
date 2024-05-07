import json

from kafka import KafkaConsumer, KafkaProducer
from neo4j import GraphDatabase
from textblob import TextBlob

uri = "neo4j://localhost:7687"
user = "neo4j"
password = "twittertwitter"
driver = GraphDatabase.driver(uri, auth=(user, password))

def get_db_session():
    return driver.session()

def update_sentiment_in_neo4j(tweet_id, sentiment_score):
    if sentiment_score > 0.1: 
        sentiment_category = "positive"
    elif sentiment_score < -0.1: 
        sentiment_category = "negative"
    else:
        sentiment_category = "neutral"

    query = """
    MATCH (tweet:Tweet {id: $tweet_id})
    MERGE (sentiment:Sentiment {type: $sentiment_category})
    MERGE (tweet)-[:HAS_SENTIMENT]->(sentiment)
    """
    with get_db_session() as session:
        session.run(query, tweet_id=tweet_id, sentiment_category=sentiment_category)


consumer = KafkaConsumer('tweet_analysis',
                         bootstrap_servers=['localhost:9092'],
                         auto_offset_reset='earliest',
                         value_deserializer=lambda m: json.loads(m.decode('utf-8')))

producer = KafkaProducer(bootstrap_servers=['localhost:9092'],
                         value_serializer=lambda v: json.dumps(v).encode('utf-8'))

for message in consumer:
    tweet = message.value
    analysis = TextBlob(tweet['text'])
    sentiment_score = analysis.sentiment.polarity
    update_sentiment_in_neo4j(tweet['tweet_id'], sentiment_score)

