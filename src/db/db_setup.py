import os
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
db_name = "autods_db"
collection_name = "functions_catalog"

client = MongoClient(mongo_uri)
db = client[db_name]
functions_catalog = db[collection_name]