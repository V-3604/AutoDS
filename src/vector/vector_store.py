#!/usr/bin/env python3
import faiss
import numpy as np
import os
import json
import sys
import logging
from pymongo import MongoClient
from dotenv import load_dotenv
import openai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutoDS")

# 1) Load environment variables (ensure OPENAI_API_KEY is set)
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY environment variable. Check .env file or system envs.")
openai.api_key = OPENAI_API_KEY

# 2) Setup MongoDB connection
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["AutoDS"]
functions_catalog = db["functions_catalog"]

def get_embedding(text: str):
    """
    Retrieve an embedding vector from OpenAI given the text.
    The model used here can be adjusted (e.g., to "text-embedding-ada-002").
    """
    response = openai.Embedding.create(
        model="text-embedding-3-small",  # Change to "text-embedding-ada-002" if preferred
        input=[text]
    )
    # Return the embedding vector as a NumPy array
    return np.array(response["data"][0]["embedding"])

def load_function_data():
    """
    Load all documents from 'functions_catalog'.
    Returns a list of text descriptions and a mapping of ID to description.
    """
    functions = list(functions_catalog.find({}, {"_id": 1, "key": 1}))
    logger.info(f"Loaded {len(functions)} functions from 'functions_catalog'")

    if not functions:
        logger.warning("No functions found. Ensure unify_database.py has been run.")

    function_map = {}
    descriptions = []
    for func in functions:
        doc_id = str(func["_id"])
        text_key = func["key"]
        function_map[doc_id] = text_key
        descriptions.append(text_key)
    return descriptions, function_map

def build_faiss_index():
    """
    Build a FAISS index using the 'key' fields from 'functions_catalog'.
    Returns the (index, descriptions, function_map).
    """
    descriptions, function_map = load_function_data()
    if not descriptions:
        logger.warning("No descriptions to embed. Stopping build process.")
        return None, [], {}

    logger.info(f"Generating embeddings for {len(descriptions)} functions.")
    batch_size = 100
    all_embeddings = []

    # Generate embeddings in batches
    for i in range(0, len(descriptions), batch_size):
        batch = descriptions[i:i + batch_size]
        total_batches = (len(descriptions) + batch_size - 1) // batch_size
        logger.info(f"Processing batch {i // batch_size + 1} of {total_batches}")
        try:
            response = openai.Embedding.create(
                model="text-embedding-3-small",  # or "text-embedding-ada-002"
                input=batch
            )
            embeddings = [np.array(item["embedding"]) for item in response["data"]]
            all_embeddings.extend(embeddings)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return None, [], {}

    if not all_embeddings:
        logger.warning("No embeddings were generated.")
        return None, [], {}

    embeddings_array = np.array(all_embeddings).astype('float32')
    dimension = embeddings_array.shape[1]

    # Build FAISS index using L2 distance
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)
    return index, descriptions, function_map

def save_faiss_index(index, descriptions, function_map):
    """
    Save the FAISS index along with descriptions and function map to files.
    """
    if index is None:
        logger.warning("No FAISS index to save; skipping save operation.")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(script_dir, exist_ok=True)

    # Save the index, descriptions, and function map
    faiss.write_index(index, os.path.join(script_dir, "functions.index"))
    with open(os.path.join(script_dir, "descriptions.txt"), "w") as f:
        f.write("\n".join(descriptions))
    with open(os.path.join(script_dir, "function_map.json"), "w") as f:
        json.dump(function_map, f)

    logger.info("Saved FAISS index, descriptions, and function map.")

def search_function(query, top_k=1):
    """
    Embed the given query, load the FAISS index, search for the closest match,
    and return the matching function document(s).
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(script_dir, "functions.index")
    if not os.path.exists(index_path):
        logger.error("No 'functions.index' found. Run the index build process first.")
        return None

    # Load the index and supporting data
    index = faiss.read_index(index_path)
    with open(os.path.join(script_dir, "descriptions.txt"), "r") as f:
        descriptions = f.read().splitlines()
    with open(os.path.join(script_dir, "function_map.json"), "r") as f:
        function_map = json.load(f)

    query_embedding = np.array([get_embedding(query)]).astype('float32')
    distances, indices = index.search(query_embedding, top_k)
    results = []
    for rank, idx in enumerate(indices[0]):
        if idx >= len(descriptions):
            continue
        desc = descriptions[idx]
        # Find corresponding document in the catalog
        matched_doc = functions_catalog.find_one({"key": desc})
        if matched_doc:
            results.append({
                "score": float(distances[0][rank]),
                "key": desc,
                "value": matched_doc["value"]
            })
    if not results:
        return None
    return results[0] if top_k == 1 else results

if __name__ == "__main__":
    logger.info("Building FAISS index from 'functions_catalog' ...")
    index, descriptions, function_map = build_faiss_index()
    if index:
        save_faiss_index(index, descriptions, function_map)
        logger.info("Vector store built successfully.")
        # Quick test of the search functionality
        test_query = "Train a decision tree"
        top_result = search_function(test_query)
        if top_result:
            logger.info(f"Test query: '{test_query}' => best match key: {top_result['key']}")
        else:
            logger.warning(f"No match found for test query '{test_query}'")
    else:
        logger.error("Failed to build the vector store index.")