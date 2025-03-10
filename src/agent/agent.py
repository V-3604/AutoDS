#!/usr/bin/env python3
import sys
import os
import logging
from pymongo import MongoClient
import json
import traceback

# Ensure we can import from sibling folders
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)

# Import the vector search function
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

    logger.info(f"Generating code snippet for {language} function: {package}.{func_name}")

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
    logger.info(f"Inferring parameters for {language} function: {package}.{func_name}")

    # Extract function arguments
    if language == "python":
        fn_args = [param.get("name", "") for param in function_details["value"].get("parameters", [])]
        defaults = [param.get("default", None) for param in function_details["value"].get("parameters", [])]
    else:  # R
        fn_args = function_details["value"].get("arguments", [])
        defaults = function_details["value"].get("defaults", [])

    # If no arguments found, use empty lists
    if not fn_args:
        fn_args = []
    if not defaults:
        defaults = [""] * len(fn_args)

    logger.info(f"Function arguments: {fn_args}")
    logger.info(f"Default values: {defaults}")

    # Build a dictionary of required parameters (those with no default)
    required_args = {}
    for i, arg in enumerate(fn_args):
        default_val = defaults[i] if i < len(defaults) else None
        if not default_val or default_val in ["", "None", "NULL"]:
            required_args[arg] = None

    logger.info(f"Required arguments: {list(required_args.keys())}")

    final_args = {}
    # First, assign user-supplied parameters matching the required args
    for req_arg in required_args:
        if req_arg in provided_args:
            final_args[req_arg] = provided_args[req_arg]

    # Include any additional provided arguments
    for arg, val in provided_args.items():
        if arg not in final_args:
            final_args[arg] = val

    # For linear regression, ensure we have formula and data
    if "linear regression" in query.lower():
        if language == "r" and "formula" not in final_args:
            final_args["formula"] = "y ~ x"

        # If data is missing and required, supply a default
        if "data" in required_args and "data" not in final_args:
            if language == "r":
                final_args["data"] = "mtcars"  # a common default dataset in R
            else:
                # For Python, provide a simple numpy array
                final_args["data"] = [[1, 2], [2, 3], [3, 4]]

    logger.info(f"Final inferred arguments: {final_args}")
    return final_args


def find_r_linear_model_function():
    """Find the R linear model function directly from the database"""
    # First, look for exact matches for stats::lm
    r_lm = functions_catalog.find_one({"value.package": "stats", "value.function_name": "lm"})

    if r_lm:
        logger.info("Found stats::lm function directly from database")
        return {
            "key": r_lm["key"],
            "value": r_lm["value"]
        }

    # Try searching with regex for similar function names
    r_lm_regex = functions_catalog.find_one({
        "key": {"$regex": "R: stats::lm"},
        "value.language": "r"
    })

    if r_lm_regex:
        logger.info("Found stats::lm function with regex search")
        return {
            "key": r_lm_regex["key"],
            "value": r_lm_regex["value"]
        }

    # Create a fallback for R's lm function if not found
    logger.info("Creating fallback for R linear regression")
    return {
        "key": "R: stats::lm - Linear Models",
        "value": {
            "language": "r",
            "package": "stats",
            "function_name": "lm",
            "arguments": ["formula", "data"],
            "defaults": ["", ""],
            "signature": "stats::lm(formula, data)",
            "docstring": "Fits Linear Models"
        }
    }


def process_query(user_query, args):
    """
    Main pipeline:
      1) Search for the best function match in the vector store.
      2) Infer any missing parameters.
      3) Generate a code snippet for transparency.
      4) Attempt to execute the function (Python or R).
    """
    logger.info(f"Processing user query: '{user_query}'")

    # Special case for linear regression - we know this is a common use case
    # and we want to make sure we get the right function
    if "linear regression" in user_query.lower() or "linear model" in user_query.lower():
        logger.info("Detected linear regression request - using R stats::lm")
        function_details = find_r_linear_model_function()
    else:
        # For other queries, use the vector store search
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
    try:
        if language == "python":
            exec_result = execute_python_function(function_details["value"], filled_args)
        elif language == "r":
            exec_result = execute_r_function(function_details["value"], filled_args)
        else:
            error_msg = f"Unknown language => {language}"
            logger.warning(error_msg)
            return {"success": False, "error": error_msg}
    except Exception as e:
        logger.error(f"Execution error: {e}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "code_snippet": code_snippet,
            "language": language
        }

    exec_result["code_snippet"] = code_snippet
    exec_result["language"] = language
    return exec_result


# Optional local test
if __name__ == "__main__":
    test_query = "linear regression"
    test_args = {"formula": "y ~ x", "data": [[1, 2], [2, 3], [3, 4]]}
    outcome = process_query(test_query, test_args)
    print("Execution outcome:", outcome)