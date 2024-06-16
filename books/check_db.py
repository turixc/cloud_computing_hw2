# check_db.py
from pymongo import MongoClient
import os

def check_mongo_connection():
    mongo_url = os.getenv('MONGO_URL', 'mongodb://mongo:27017/BooksDB')
    client = MongoClient(mongo_url)
    try:
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        print("MongoDB connection successful")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")

if __name__ == "__main__":
    check_mongo_connection()
