import json
import pymongo

# Connect to MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["autods"]
functions_collection = db["functions"]

def seed_data():
    with open("src/data/functions.json", "r") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("❌ ERROR: functions.json should be a list of function objects.")
        return

    # Clear existing data
    functions_collection.delete_many({})

    # Insert new data
    functions_collection.insert_many(data)
    print("✅ Seeded function data into MongoDB!")

if __name__ == "__main__":
    seed_data()
