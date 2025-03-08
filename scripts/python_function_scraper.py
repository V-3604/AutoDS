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
    "python-dotenv"
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
    "matplotlib", "seaborn", "plotly",

    # Machine learning
    "sklearn", "xgboost", "lightgbm",

    # Deep learning (only if needed)
    # "tensorflow", "keras", "torch",

    # NLP (if needed)
    # "nltk", "spacy",

    # Data processing
    "sqlalchemy", "requests",

    # Statistical analysis
    "statsmodels",

    # Utilities
    "joblib"
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
                    if not is_pkg:
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


def generate_embeddings(texts: List[str]) -> Optional[List[np.ndarray]]:
    """Generate embeddings using OpenAI API"""
    if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
        return None

    try:
        batch_size = 100  # OpenAI recommends batching requests
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(
                f"Processing embedding batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}")

            try:
                response = openai.Embedding.create(
                    input=batch,
                    model="text-embedding-3-small"
                )
                batch_embeddings = [np.array(item['embedding']) for item in response['data']]
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
                return None

        return embeddings

    except Exception as e:
        logger.error(f"Error in embedding generation: {e}")
        return None


def build_faiss_index():
    """Build FAISS index for function search"""
    if not FAISS_AVAILABLE:
        logger.warning("FAISS not available. Skipping index building.")
        return

    logger.info("Building FAISS index for function search")

    try:
        # Connect to MongoDB
        client = get_mongo_client()
        db = client["AutoDS"]
        collection = db["python_functions"]

        # Get all functions
        all_functions = []
        cursor = collection.find({})

        for func in cursor:
            # Create a search key from function name and docstring
            key = f"{func.get('package', '')}.{func.get('function_name', '')}: {func.get('docstring', '')[:100]}"
            all_functions.append({
                "id": str(func["_id"]),
                "key": key,
                "package": func.get("package", ""),
                "function_name": func.get("function_name", ""),
                "docstring": func.get("docstring", "")
            })

        client.close()

        if not all_functions:
            logger.warning("No functions found to index")
            return

        # Generate embeddings if OpenAI is available
        if OPENAI_AVAILABLE and OPENAI_API_KEY:
            logger.info(f"Generating embeddings for {len(all_functions)} functions")
            function_texts = [func["key"] for func in all_functions]
            embeddings = generate_embeddings(function_texts)

            if embeddings:
                # Create FAISS index
                embeddings_array = np.array(embeddings).astype('float32')
                dimension = embeddings_array.shape[1]
                index = faiss.IndexFlatL2(dimension)
                index.add(embeddings_array)

                # Save the index and function IDs
                faiss.write_index(index, "python_function_index.bin")
                with open("python_function_ids.json", "w") as f:
                    json.dump([{"id": func["id"], "key": func["key"]} for func in all_functions], f)

                logger.info(f"FAISS index created with {len(embeddings)} functions")
            else:
                logger.warning("No embeddings generated")
        else:
            logger.warning("OpenAI API key not provided, skipping embedding generation")

    except Exception as e:
        logger.error(f"Error building FAISS index: {e}")
        logger.error(traceback.format_exc())


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

        # Log summary
        logger.info("Database expansion completed:")
        logger.info(f"  - Attempted to process {len(packages)} packages")
        logger.info(f"  - Successfully processed {len(processed_packages)} packages")
        logger.info(f"  - Failed to process {len(failed_packages)} packages")
        logger.info(f"  - Total functions stored: {total_functions}")

        # Build FAISS index if functions were stored
        if total_functions > 0:
            build_faiss_index()
        else:
            logger.warning("No functions stored, skipping FAISS index building")

        logger.info("Database expansion completed")

    except Exception as e:
        logger.error(f"Error in main function: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()