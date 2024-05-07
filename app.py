from bson.json_util import dumps
from flask import Flask, jsonify, request
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient('mongodb://localhost:27017/')
db = client['twitter']  
user_collection = db['users'] 
tweet_collection = db['tweets']

@app.route('/')
def home():
    return "Welcome to the Flask MongoDB app!"

@app.route('/add_tweet', methods=['POST'])
def add_tweet():
    """Adds a new user to the users collection."""
    tweet_data = request.json
    if tweet_data:
        tweet_collection.insert_one(tweet_data)
        return jsonify({"message": "tweet added successfully"}), 201
    else:
        return jsonify({"message": "Empty request"}), 400
    
@app.route('/add_user', methods=['POST'])
def add_user():
    """Adds a new user to the users collection."""
    user_data = request.json
    if user_data:
        user_collection.insert_one(user_data)
        return jsonify({"message": "User added successfully"}), 201
    else:
        return jsonify({"message": "Empty request"}), 400

@app.route('/users', methods=['GET'])
def get_users():
    """Retrieves all users from the users collection."""
    users = user_collection.find({})
    result = [user for user in users]
    return jsonify(result), 200

@app.route('/users/<username>', methods=['GET'])
def get_user(username):
    """Retrieves a single user from the users collection by username."""
    user = user_collection.find_one({"username": username})
    if user:
        return dumps(user), 200
    else:
        return jsonify({"message": "User not found"}), 404

if __name__ == '__main__':
    app.run(debug=True,port=5002)

