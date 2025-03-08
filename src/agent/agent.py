#!/usr/bin/env python3
import sys
import os
import logging
from pymongo import MongoClient
import json

# Ensure we can import from sibling or parent folders if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports from local modules
from vector.vector_store import search_function
from execution.python_exec import execute_python_function
from execution.r_exec import execute_r_function

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutoDS")

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["AutoDS"]
functions_catalog = db["functions_catalog"]

def generate_code_snippet(function_details, args):
    """
    Generate an illustrative or runnable code snippet for either Python or R,
    showing how the function was called with the inferred arguments.
    """
    language = function_details["value"]["language"]
    package = function_details["value"]["package"]
    func_name = function_details["value"]["function_name"]

    # Format arguments based on their types
    formatted_args = []
    for arg_key, arg_val in args.items():
        if isinstance(arg_val, str):
            val_str = f'"{arg_val}"'
        elif isinstance(arg_val, list):
            # For lists of lists, create an R-like syntax; otherwise, use simple Python string conversion
            if language == "python":
                val_str = str(arg_val)
            else:  # R
                if all(isinstance(x, list) for x in arg_val):
                    rows = [f"c({', '.join(map(str, row))})" for row in arg_val]
                    val_str = f"rbind({', '.join(rows)})"
                else:
                    val_str = f"c({', '.join(map(str, arg_val))})"
        else:
            val_str = str(arg_val)

        formatted_args.append(f"{arg_key}={val_str}")

    # Build the final snippet per language
    if language == "python":
        code = (
            f"import {package}\n"
            f"{package}.{func_name}({', '.join(formatted_args)})"
        )
    else:  # R
        code = (
            f"library({package})\n"
            f"{package}::{func_name}({', '.join(formatted_args)})"
        )

    return code

def infer_parameters(function_details, query, provided_args):
    """
    Intelligently fill in missing function parameters based on the function's
    defined arguments and any provided user-supplied values.
    """
    language = function_details["value"]["language"]
    package = function_details["value"]["package"]
    func_name = function_details["value"]["function_name"]
    logger.info(f"Infer parameters for {language} function: {package}.{func_name}")

    fn_args = function_details["value"].get("arguments", [])
    defaults = function_details["value"].get("defaults", [])

    # Build a dictionary of required parameters (those with no default)
    required_args = {}
    for i, arg in enumerate(fn_args):
        default_val = defaults[i] if i < len(defaults) else None
        if not default_val or default_val in ["", "None"]:
            required_args[arg] = None

    final_args = {}
    # First, assign user-supplied parameters matching the required args
    for req_arg in required_args:
        if req_arg in provided_args:
            final_args[req_arg] = provided_args[req_arg]

    # Include any additional provided arguments
    for arg, val in provided_args.items():
        if arg not in final_args:
            final_args[arg] = val

    # If data is missing and required, supply a default based on language
    if "data" in required_args and "data" not in final_args:
        if language == "r":
            final_args["data"] = "iris"  # a common default dataset in R

    return final_args

def process_query(user_query, args):
    """
    Main pipeline:
      1) Search for the best function match in the vector store.
      2) Infer any missing parameters.
      3) Generate a code snippet for transparency.
      4) Attempt to execute the function (Python or R).
    """
    logger.info(f"Processing user query: '{user_query}'")

    # Search using the vector store
    function_details = search_function(user_query)
    if not function_details:
        logger.warning("No function found for that query.")
        return {"success": False, "error": "No matching function found"}

    logger.info(f"Best match => {function_details['key']}")

    # Infer parameters based on provided args and function signature
    filled_args = infer_parameters(function_details, user_query, args)
    logger.info(f"Inferred arguments => {filled_args}")

    # Generate a code snippet to show the running example
    code_snippet = generate_code_snippet(function_details, filled_args)
    language = function_details["value"]["language"]
    logger.info(f"Detected language => {language}")

    # Execute based on language
    if language == "python":
        exec_result = execute_python_function(function_details["value"], filled_args)
    elif language == "r":
        exec_result = execute_r_function(function_details["value"], filled_args)
    else:
        error_msg = f"Unknown language => {language}"
        logger.warning(error_msg)
        return {"success": False, "error": error_msg}

    exec_result["code_snippet"] = code_snippet
    exec_result["language"] = language
    return exec_result

# Optional local test
if __name__ == "__main__":
    test_query = "linear regression"
    test_args = {"formula": "y ~ x", "data": [[1, 2], [2, 3], [3, 4]]}
    outcome = process_query(test_query, test_args)
    print("Execution outcome:", outcome)