import pymongo
from vector.vector_store import search_function
from execution.python_exec import execute_python_function
from execution.r_exec import execute_r_function

# Connect to MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["autods"]
functions_collection = db["functions"]

def process_query(user_query, args):
    """
    Processes a user query, retrieves the appropriate function, and executes it.

    :param user_query: The function description provided by the user (e.g., "linear regression").
    :param args: Dictionary of function arguments (e.g., {"formula": ..., "data": ...}).
    :return: Dictionary with execution result or error details.
    """
    print(f"Processing query: {user_query}")

    # Retrieve function details from vector store (FAISS)
    function_details = search_function(user_query)

    if not function_details:
        print("❌ No function found in vector store.")
        return {"success": False, "error": "Function not found in vector store"}

    print(f"🔍 Matched function: {function_details['key']}")
    print(f"✅ Function metadata found: {function_details}")

    # Access language from the 'value' sub-dictionary
    language = function_details["value"]["language"]

    # Check if it's a Python or R function and execute accordingly
    if language == "python":
        return execute_python_function(function_details["value"], args)
    elif language == "r":
        return execute_r_function(function_details["value"], args)

    print(f"❌ Unknown function language: {language}")
    return {"success": False, "error": f"Unknown function language: {language}"}

# Optional: Test the function locally (remove in production)
if __name__ == "__main__":
    test_query = "linear regression"
    test_args = {"formula": "y ~ x", "data": [[1, 2], [2, 3], [3, 4]]}
    result = process_query(test_query, test_args)
    print("Execution result:", result)