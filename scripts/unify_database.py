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
        short_doc = docstring[:100]
        key = f"Python: {package}.{func_name} - {short_doc}"
        python_catalog.append({
            "key": key,
            "value": {
                "language": "python",
                "package": package,
                "function_name": func_name,
                "arguments": func.get("arguments", []),
                "defaults": func.get("default_values", []),
                "signature": func.get("signature", ""),
                "docstring": docstring
            }
        })

    # 5) Convert R docs into the same key/value format
    r_catalog = []
    for func in r_functions:
        package = func.get("package", "")
        func_name = func.get("function_name", "")
        description = func.get("description", "")
        short_desc = description[:100]
        key = f"R: {package}::{func_name} - {short_desc}"
        r_catalog.append({
            "key": key,
            "value": {
                "language": "r",
                "package": package,
                "function_name": func_name,
                "arguments": func.get("arguments", []),
                "defaults": func.get("default_values", []),
                "signature": func.get("full_function_call", ""),
                "docstring": description
            }
        })

    # 6) Merge and insert into 'functions_catalog'
    all_catalog = python_catalog + r_catalog
    if all_catalog:
        db.functions_catalog.insert_many(all_catalog)
        logger.info(f"Inserted {len(all_catalog)} total functions into 'functions_catalog'")
    else:
        logger.warning("No functions found to unify (both Python and R lists were empty).")

    # 7) Cleanup
    client.close()


if __name__ == "__main__":
    unify_database()