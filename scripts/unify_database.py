#!/usr/bin/env python3

import os
import sys
import logging
from pymongo import MongoClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutoDS")


def unify_database():
    """
    Unify Python and R functions into a consistent format in the
    'functions_catalog' collection. This catalog is used for vector search.
    """
    client = MongoClient("mongodb://localhost:27017/")
    db = client["AutoDS"]

    # 1) Pull all Python function documents
    python_functions = list(db.python_functions.find({}))
    logger.info(f"Found {len(python_functions)} Python functions from python_functions collection")

    # 2) Pull all R function documents
    r_functions = list(db.r_functions.find({}))
    logger.info(f"Found {len(r_functions)} R functions from r_functions collection")

    # 3) Clear out (or create) the 'functions_catalog' collection
    if "functions_catalog" in db.list_collection_names():
        db.functions_catalog.delete_many({})
        logger.info("Cleared existing functions_catalog collection")

    # 4) Convert Python docs into a consistent key/value format
    python_catalog = []
    for func in python_functions:
        package = func.get("package", "")
        func_name = func.get("function_name", "")
        docstring = func.get("docstring", "")
        parameters = func.get("parameters", [])

        # Create a short description from the docstring
        short_doc = docstring[:100] if docstring else f"Python function {package}.{func_name}"

        # Create a consistent key format
        key = f"Python: {package}.{func_name} - {short_doc}"

        # Default values for parameters
        default_values = []
        if parameters:
            default_values = [param.get("default", "") for param in parameters]

        python_catalog.append({
            "key": key,
            "value": {
                "language": "python",
                "package": package,
                "function_name": func_name,
                "arguments": [p.get("name", "") for p in parameters],
                "defaults": default_values,
                "signature": func.get("signature", ""),
                "docstring": docstring,
                "parameters": parameters  # Keep the full parameter info
            }
        })

    # 5) Convert R docs into the same key/value format
    r_catalog = []
    for func in r_functions:
        package = func.get("package", "")
        func_name = func.get("function_name", "")
        description = func.get("description", "")
        arguments = func.get("arguments", [])

        # Create a short description
        short_desc = description[:100] if description else f"R function {package}::{func_name}"

        # Create a consistent key format
        key = f"R: {package}::{func_name} - {short_desc}"

        # Default values for arguments
        default_values = []
        if arguments:
            default_values = [arg.get("default", "") for arg in arguments]

        r_catalog.append({
            "key": key,
            "value": {
                "language": "r",
                "package": package,
                "function_name": func_name,
                "arguments": [arg.get("name", "") for arg in arguments],
                "defaults": default_values,
                "signature": func.get("full_function_call", ""),
                "docstring": description
            }
        })

    # 6) Ensure we have the critical stats::lm function for linear regression
    lm_exists = any(
        item["value"]["package"] == "stats" and item["value"]["function_name"] == "lm" for item in r_catalog)
    if not lm_exists:
        logger.warning("Adding fallback entry for stats::lm (linear regression)")
        r_catalog.append({
            "key": "R: stats::lm - Linear Models for regression analysis",
            "value": {
                "language": "r",
                "package": "stats",
                "function_name": "lm",
                "arguments": ["formula", "data"],
                "defaults": ["", ""],
                "signature": "stats::lm(formula, data, ...)",
                "docstring": "Fits Linear Models. The lm function is used to fit linear models."
            }
        })

    # 7) Add explicit entries for common data science tasks to improve matching
    common_tasks = [
        {
            "key": "R: stats::lm - Perform linear regression on data",
            "value": {
                "language": "r",
                "package": "stats",
                "function_name": "lm",
                "arguments": ["formula", "data"],
                "defaults": ["", ""],
                "signature": "stats::lm(formula, data, ...)",
                "docstring": "Linear regression modeling for statistical analysis. Used to fit linear models to data."
            }
        },
        {
            "key": "R: stats::t.test - Perform t-test for statistical significance",
            "value": {
                "language": "r",
                "package": "stats",
                "function_name": "t.test",
                "arguments": ["x", "y"],
                "defaults": ["", "NULL"],
                "signature": "stats::t.test(x, y = NULL, ...)",
                "docstring": "Student's t-test for comparing means between samples."
            }
        },
        {
            "key": "R: stats::cor - Calculate correlation between variables",
            "value": {
                "language": "r",
                "package": "stats",
                "function_name": "cor",
                "arguments": ["x", "y"],
                "defaults": ["", "NULL"],
                "signature": "stats::cor(x, y = NULL, ...)",
                "docstring": "Correlation coefficient calculation between variables."
            }
        }
    ]

    # Add the common tasks to the catalog
    r_catalog.extend(common_tasks)
    logger.info(f"Added {len(common_tasks)} explicit entries for common data science tasks")

    # 8) Merge and insert into 'functions_catalog'
    all_catalog = python_catalog + r_catalog
    if all_catalog:
        db.functions_catalog.insert_many(all_catalog)
        logger.info(f"Inserted {len(all_catalog)} total functions into 'functions_catalog'")

        # Log samples of what we inserted
        if python_catalog:
            logger.info(f"Sample Python function: {python_catalog[0]['key']}")
        if r_catalog:
            logger.info(f"Sample R function: {r_catalog[0]['key']}")
    else:
        logger.warning("No functions found to unify (both Python and R lists were empty).")

    # 9) Create indexes for faster lookups
    db.functions_catalog.create_index("key")
    logger.info("Created index on 'key' field in functions_catalog")

    # 10) Verify linear regression function exists
    lr_check = db.functions_catalog.find_one({"key": {"$regex": "linear regression", "$options": "i"}})
    if lr_check:
        logger.info("✓ Linear regression function found in database")
    else:
        logger.warning("⚠ Linear regression function not found in database!")

    # 11) Check specifically for stats::lm
    lm_check = db.functions_catalog.find_one({"value.package": "stats", "value.function_name": "lm"})
    if lm_check:
        logger.info("✓ stats::lm function found in database")
    else:
        logger.warning("⚠ stats::lm function not found in database!")

    # 12) Cleanup
    client.close()


if __name__ == "__main__":
    unify_database()