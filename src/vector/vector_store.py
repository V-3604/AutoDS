import faiss
import numpy as np
import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Retrieve OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key! Ensure it's set in the .env file.")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Connect to MongoDB
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client.autods_db
functions_catalog = db.functions_catalog  # Corrected to ensure proper MongoDB usage

# Function to fetch OpenAI Embeddings
def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=[text]
    )
    return np.array(response.data[0].embedding)

# Load function descriptions from MongoDB
def load_function_data():
    functions = list(functions_catalog.find({}, {"_id": 0, "key": 1}))  # Fetch only 'key' field
    descriptions = [f["key"] for f in functions]  # Extract function keys
    return descriptions

# Create FAISS index and store embeddings
def build_faiss_index():
    descriptions = load_function_data()
    if not descriptions:
        print("No functions found in the database.")
        return None, []

    embeddings = np.array([get_embedding(desc) for desc in descriptions])
    index = faiss.IndexFlatL2(embeddings.shape[1])  # L2 distance-based FAISS index
    index.add(embeddings)

    return index, descriptions

# Save FAISS index and function descriptions
def save_faiss_index(index, descriptions):
    if index is None:
        print("No FAISS index to save.")
        return

    faiss.write_index(index, "src/vector/functions.index")  # Save FAISS index
    with open("src/vector/descriptions.txt", "w") as f:
        f.write("\n".join(descriptions))  # Save descriptions
    print("FAISS index and descriptions saved.")

# Function to search for the best-matching function
def search_function(query, top_k=1):
    if not os.path.exists("src/vector/functions.index"):
        print("FAISS index not found. Run vector_store.py first.")
        return None

    # Load FAISS index
    index = faiss.read_index("src/vector/functions.index")

    # Load function descriptions
    with open("src/vector/descriptions.txt", "r") as f:
        descriptions = f.read().splitlines()

    # Convert query to embedding
    query_embedding = np.array([get_embedding(query)])

    # Search FAISS for the closest match
    _, indices = index.search(query_embedding, top_k)

    # Retrieve the best match
    best_match_index = indices[0][0]
    if best_match_index >= len(descriptions):
        print("No valid match found.")
        return None

    best_match_desc = descriptions[best_match_index]
    matched_function = functions_catalog.find_one({"key": best_match_desc})  # Corrected MongoDB query

    return matched_function

# Ensure function is executed correctly
if __name__ == "__main__":
    index, descriptions = build_faiss_index()
    if index:
        save_faiss_index(index, descriptions)

    # Test function retrieval
    test_query = "Train decision tree"
    result = search_function(test_query)

    if result:
        print("Best function match found:", result)
    else:
        print("No matching function found.")
