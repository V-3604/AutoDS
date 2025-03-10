#!/usr/bin/env python3
"""
AutoDS Database Expansion Script for Python
This script expands the function database by:
1. Scraping core Python packages needed for AutoDS
2. Extracting function details from each package
3. Storing the data in MongoDB
4. Building a FAISS index for semantic search
"""

import importlib
import inspect
import json
import time
import sys
import traceback
import logging
import os
import subprocess
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("database_expansion.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AutoDS")

# Try to import required packages, install if missing
required_packages = [
    "pymongo",
    "numpy",
    "faiss-cpu",
    "openai",
    "python-dotenv",
    "scipy",
    "scikit-learn",
    "pandas",
    "matplotlib"
]

for package in required_packages:
    try:
        importlib.import_module(package.replace("-", "_"))
    except ImportError:
        logger.info(f"Installing required package: {package}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Now import after ensuring they're installed
import numpy as np
from pymongo import MongoClient, errors
from dotenv import load_dotenv

# Try to import faiss
try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available. Index building will be skipped.")

# Try to import OpenAI
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available. Embedding generation will be skipped.")

# Load environment variables
load_dotenv()

# Setup OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    logger.warning("OpenAI API key not found in environment variables.")


# MongoDB connection with retry
def get_mongo_client(max_retries=3):
    for attempt in range(max_retries):
        try:
            return MongoClient("mongodb://localhost:27017/", maxPoolSize=50)
        except errors.ConnectionFailure as e:
            if attempt < max_retries - 1:
                logger.warning(f"MongoDB connection attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(2)
            else:
                logger.error(f"Failed to connect to MongoDB after {max_retries} attempts: {e}")
                raise


# Core Python packages needed for AutoDS
AUTODS_PYTHON_PACKAGES = [
    # Core data science
    "numpy", "pandas", "scipy",

    # Visualization
    "matplotlib", "seaborn",

    # Machine learning
    "sklearn",

    # Statistical analysis
    "statsmodels",

    # Utilities
    "math"
]


def check_package_installed(package_name):
    """Check if a package is installed and importable"""
    spec = importlib.util.find_spec(package_name.split('.')[0])
    return spec is not None


def install_package(package_name):
    """Attempt to install a package with pip"""
    logger.info(f"Attempting to install {package_name}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--no-cache-dir"])
        return True
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to install {package_name}: {e}")
        return False


def get_available_packages():
    """Get a list of available packages, installing missing ones"""
    logger.info("Checking for installed packages")

    installed_packages = []
    failed_packages = []

    for package in AUTODS_PYTHON_PACKAGES:
        if check_package_installed(package):
            installed_packages.append(package)
        else:
            if install_package(package):
                installed_packages.append(package)
            else:
                failed_packages.append(package)

    logger.info(f"Successfully installed/found {len(installed_packages)} packages")
    if failed_packages:
        logger.warning(f"Failed to install {len(failed_packages)} packages: {', '.join(failed_packages)}")

    return installed_packages


def extract_function_details(func_obj, module_name, func_name):
    """Extract details from a function object with improved error handling"""
    try:
        # Skip special methods and properties
        if func_name.startswith('__') and func_name.endswith('__'):
            return None

        if isinstance(func_obj, property):
            return None

        # Get function signature
        signature = inspect.signature(func_obj)
        docstring = inspect.getdoc(func_obj) or ""

        # Extract parameters
        params = []
        for param_name, param in signature.parameters.items():
            param_info = {
                "name": param_name,
                "kind": str(param.kind),
                "default": None if param.default is inspect.Parameter.empty else str(param.default),
                "annotation": None if param.annotation is inspect.Parameter.empty else str(param.annotation)
            }
            params.append(param_info)

        # Get return annotation
        return_annotation = None if signature.return_annotation is inspect.Parameter.empty else str(
            signature.return_annotation)

        # Build function info
        function_info = {
            "package": module_name.split('.')[0],
            "module": module_name,
            "function_name": func_name,
            "signature": str(signature),
            "parameters": params,
            "return_annotation": return_annotation,
            "docstring": docstring,
            "full_function_call": f"{module_name}.{func_name}()",
            "language": "python"
        }

        return function_info
    except Exception as e:
        logger.debug(f"Error extracting details for {module_name}.{func_name}: {e}")
        return None


def extract_module_functions(module_name):
    """Extract functions from a module"""
    start_time = time.time()
    function_records = []

    try:
        # Import the module
        module = importlib.import_module(module_name)

        # Process regular functions
        for name, obj in inspect.getmembers(module):
            if name.startswith('_'):
                continue

            try:
                if inspect.isfunction(obj):
                    function_data = extract_function_details(obj, module_name, name)
                    if function_data:
                        function_records.append(function_data)
                elif inspect.isclass(obj):
                    # Process class methods
                    for method_name, method_obj in inspect.getmembers(obj, predicate=inspect.isfunction):
                        if not method_name.startswith('_'):
                            method_data = extract_function_details(
                                method_obj,
                                f"{module_name}.{name}",
                                method_name
                            )
                            if method_data:
                                function_records.append(method_data)
            except Exception as e:
                logger.debug(f"Skipping {name} in {module_name}: {e}")

        processing_time = time.time() - start_time
        logger.info(f"Extracted {len(function_records)} functions from {module_name} in {processing_time:.2f} seconds")
        return function_records

    except Exception as e:
        processing_time = time.time() - start_time
        logger.warning(f"Failed to process module {module_name}: {e}")
        return []


def process_package(package_name):
    """Process a package and its submodules"""
    logger.info(f"Starting to process package: {package_name}")
    start_time = time.time()
    all_functions = []

    try:
        # Import the main package
        package = importlib.import_module(package_name)

        # Process main module functions
        main_module_functions = extract_module_functions(package_name)
        all_functions.extend(main_module_functions)

        # Process submodules if available
        if hasattr(package, "__path__"):
            try:
                import pkgutil
                for _, submodule_name, is_pkg in pkgutil.iter_modules(package.__path__, package_name + "."):
                    if not is_pkg and not submodule_name.endswith('._') and not '_._' in submodule_name:
                        try:
                            submodule_functions = extract_module_functions(submodule_name)
                            all_functions.extend(submodule_functions)
                        except Exception as e:
                            logger.debug(f"Error processing submodule {submodule_name}: {e}")
            except Exception as e:
                logger.debug(f"Error finding submodules for {package_name}: {e}")

    except Exception as e:
        logger.warning(f"Failed to process package {package_name}: {e}")
        logger.debug(traceback.format_exc())

    processing_time = time.time() - start_time
    logger.info(
        f"Finished processing package {package_name} in {processing_time:.2f} seconds, found {len(all_functions)} functions")

    return all_functions


def store_functions_mongo(functions):
    """Store extracted functions in MongoDB"""
    if not functions:
        return 0

    try:
        client = get_mongo_client()
        db = client["AutoDS"]
        collection = db["python_functions"]

        # Insert in batches to avoid issues with large datasets
        batch_size = 100
        inserted_count = 0

        for i in range(0, len(functions), batch_size):
            batch = functions[i:i + batch_size]
            try:
                result = collection.insert_many(batch)
                inserted_count += len(result.inserted_ids)
            except Exception as e:
                logger.error(f"Error in batch insertion: {e}")

        client.close()
        return inserted_count

    except Exception as e:
        logger.error(f"Error storing functions: {e}")
        logger.error(traceback.format_exc())
        return 0


def add_linear_regression_functions():
    """Add specific linear regression functions to ensure they're available"""
    try:
        client = get_mongo_client()
        db = client["AutoDS"]
        collection = db["python_functions"]

        # Check if we need to add sklearn LinearRegression
        lr_exists = collection.count_documents({
            "package": "sklearn.linear_model",
            "function_name": "LinearRegression"
        })

        if lr_exists == 0:
            logger.info("Adding sklearn.linear_model.LinearRegression manually")
            lr_function = {
                "package": "sklearn.linear_model",
                "module": "sklearn.linear_model",
                "function_name": "LinearRegression",
                "signature": "LinearRegression(fit_intercept=True, normalize=False, copy_X=True, n_jobs=None, positive=False)",
                "parameters": [
                    {"name": "fit_intercept", "kind": "POSITIONAL_OR_KEYWORD", "default": "True"},
                    {"name": "normalize", "kind": "POSITIONAL_OR_KEYWORD", "default": "False"},
                    {"name": "copy_X", "kind": "POSITIONAL_OR_KEYWORD", "default": "True"},
                    {"name": "n_jobs", "kind": "POSITIONAL_OR_KEYWORD", "default": "None"},
                    {"name": "positive", "kind": "POSITIONAL_OR_KEYWORD", "default": "False"}
                ],
                "return_annotation": None,
                "docstring": "Ordinary least squares Linear Regression. LinearRegression fits a linear model with coefficients w = (w1, …, wp) to minimize the residual sum of squares between the observed targets in the dataset, and the targets predicted by the linear approximation.",
                "full_function_call": "sklearn.linear_model.LinearRegression()",
                "language": "python"
            }
            collection.insert_one(lr_function)
            logger.info("Added sklearn.linear_model.LinearRegression to database")

        # Check if we need to add scipy.stats.linregress
        linregress_exists = collection.count_documents({
            "package": "scipy.stats",
            "function_name": "linregress"
        })

        if linregress_exists == 0:
            logger.info("Adding scipy.stats.linregress manually")
            linregress_function = {
                "package": "scipy.stats",
                "module": "scipy.stats",
                "function_name": "linregress",
                "signature": "linregress(x, y=None)",
                "parameters": [
                    {"name": "x", "kind": "POSITIONAL_OR_KEYWORD", "default": None},
                    {"name": "y", "kind": "POSITIONAL_OR_KEYWORD", "default": "None"}
                ],
                "return_annotation": None,
                "docstring": "Calculate a linear regression for two sets of measurements. The linear regression calculates the best fit line for the observed data by minimizing the sum of the squares of the vertical deviations from each data point to the line.",
                "full_function_call": "scipy.stats.linregress(x, y)",
                "language": "python"
            }
            collection.insert_one(linregress_function)
            logger.info("Added scipy.stats.linregress to database")

        client.close()

    except Exception as e:
        logger.error(f"Error adding linear regression functions: {e}")


def main():
    """Main function to coordinate processing"""
    logger.info("Starting AutoDS database expansion for Python functions")

    try:
        # Clear existing data
        client = get_mongo_client()
        db = client["AutoDS"]
        collection = db["python_functions"]

        before_count = collection.count_documents({})
        logger.info(f"Current Python function count: {before_count}")

        collection.delete_many({})
        logger.info("Cleared existing Python functions")

        client.close()

        # Get list of packages to process
        packages = get_available_packages()
        logger.info(f"Found {len(packages)} packages to process")

        total_functions = 0
        processed_packages = []
        failed_packages = []

        # Process each package
        for i, package in enumerate(packages):
            try:
                logger.info(f"Processing package {i + 1}/{len(packages)}: {package}")

                functions = process_package(package)

                if functions:
                    inserted = store_functions_mongo(functions)
                    logger.info(f"Stored {inserted} functions from {package}")
                    total_functions += inserted
                    processed_packages.append(package)
                else:
                    logger.warning(f"No functions extracted from {package}")
                    failed_packages.append(package)

                logger.info(f"[{i + 1}/{len(packages)}] Processed {package}")

            except Exception as e:
                logger.error(f"Error processing package {package}: {e}")
                logger.error(traceback.format_exc())
                failed_packages.append(package)

        # Add linear regression functions manually
        add_linear_regression_functions()

        # Log summary
        logger.info("Database expansion completed:")
        logger.info(f"  - Attempted to process {len(packages)} packages")
        logger.info(f"  - Successfully processed {len(processed_packages)} packages")
        logger.info(f"  - Failed to process {len(failed_packages)} packages")
        logger.info(f"  - Total functions stored: {total_functions}")

        logger.info("Database expansion completed")

    except Exception as e:
        logger.error(f"Error in main function: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()