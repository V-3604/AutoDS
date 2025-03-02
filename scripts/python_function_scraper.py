"""
AutoDS Database Expansion Script
This script expands the function database by:
1. Automating the scraping of 100+ Python packages
2. Extracting function details from each package
3. Storing the data in MongoDB
4. Testing the scalability of the approach
"""

import importlib
import inspect
import json
import time
import sys
import requests
import os
from pymongo import MongoClient
from concurrent.futures import ThreadPoolExecutor
import logging
import numpy as np
import faiss
from openai import OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
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


# MongoDB connection
def get_mongo_client():
    """Get MongoDB client with connection pooling"""
    return MongoClient("mongodb://localhost:27017/", maxPoolSize=50)


# List of popular Python packages to analyze
# This list can be expanded or loaded from a file
PYTHON_PACKAGES = [
    # Core data science
    "numpy", "pandas", "scipy", "matplotlib", "seaborn", "plotly", "bokeh",
    "statsmodels", "patsy",

    # Machine learning
    "sklearn", "xgboost", "lightgbm", "catboost", "tensorflow", "keras",
    "torch", "transformers", "gensim", "spacy", "nltk", "textblob",

    # Data processing
    "dask", "vaex", "polars", "pyarrow", "fastparquet", "sqlalchemy", "beautifulsoup4",
    "lxml", "html5lib", "requests", "aiohttp", "httpx",

    # Optimization and numerical computing
    "sympy", "cvxpy", "pulp", "pyomo", "numba", "cython",

    # Visualization and dashboards
    "dash", "streamlit", "gradio", "altair", "folium", "geopandas", "networkx",

    # Time series
    "prophet", "pmdarima", "statsforecast", "tslearn", "tsfresh",

    # Image processing
    "pillow", "opencv-python", "scikit-image", "albumentations",

    # Natural language processing
    "transformers", "sentence-transformers", "flair", "stanza",

    # Miscellaneous
    "tqdm", "joblib", "pytest", "ipywidgets", "pyyaml", "ujson", "fastapi",
    "flask", "django", "pydantic"
]


# A more comprehensive approach would be to get top packages from PyPI
def get_top_pypi_packages(limit=100):
    """Get top packages from PyPI based on download counts"""
    try:
        # This is a simplified version - PyPI doesn't have a direct API for this
        # In a real implementation, you might need to scrape or use a third-party service
        response = requests.get("https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.json")
        if response.status_code == 200:
            packages = response.json().get("rows", [])
            return [package["project"] for package in packages[:limit]]
        return PYTHON_PACKAGES
    except Exception as e:
        logger.error(f"Error fetching PyPI packages: {e}")
        return PYTHON_PACKAGES


def extract_function_details(func_obj, module_name, func_name):
    """Extract detailed information about a function"""
    try:
        # Get signature and docstring
        signature = inspect.signature(func_obj)
        docstring = inspect.getdoc(func_obj) or ""

        # Get parameter details
        params = {}
        for param_name, param in signature.parameters.items():
            param_info = {
                "kind": str(param.kind),
                "default": str(param.default) if param.default is not inspect.Parameter.empty else None,
                "annotation": str(param.annotation) if param.annotation is not inspect.Parameter.empty else None
            }
            params[param_name] = param_info

        # Get return annotation
        return_annotation = str(
            signature.return_annotation) if signature.return_annotation is not inspect.Parameter.empty else None

        return {
            "module": module_name,
            "name": func_name,
            "signature": str(signature),
            "parameters": params,
            "return_annotation": return_annotation,
            "docstring": docstring
        }
    except Exception as e:
        logger.warning(f"Error extracting details for {module_name}.{func_name}: {e}")
        return {
            "module": module_name,
            "name": func_name,
            "error": str(e)
        }


def extract_module_functions(module_name):
    """Extract all function and class information from a module"""
    start_time = time.time()
    try:
        # Try to import the module
        module = importlib.import_module(module_name)
        functions = {}
        classes = {}

        # Process direct members of the module
        for name, obj in inspect.getmembers(module):
            # Skip private/dunder names
            if name.startswith('_'):
                continue

            try:
                if inspect.isfunction(obj):
                    functions[name] = extract_function_details(obj, module_name, name)
                elif inspect.isclass(obj):
                    # For classes, gather methods
                    class_info = {"name": name, "module": module_name, "methods": {}}

                    # Get class methods
                    for method_name, method_obj in inspect.getmembers(obj, predicate=inspect.isfunction):
                        if not method_name.startswith('_'):  # Skip private methods
                            try:
                                class_info["methods"][method_name] = extract_function_details(
                                    method_obj, f"{module_name}.{name}", method_name
                                )
                            except Exception as e:
                                logger.debug(f"Skipping method {method_name} in class {name}: {e}")

                    classes[name] = class_info
            except Exception as e:
                logger.debug(f"Skipping {name} in {module_name}: {e}")

        # Record processing time for metrics
        processing_time = time.time() - start_time

        return {
            "module": module_name,
            "functions": functions,
            "classes": classes,
            "processing_time": processing_time,
            "status": "success"
        }
    except Exception as e:
        processing_time = time.time() - start_time
        logger.warning(f"Failed to process module {module_name}: {e}")
        return {
            "module": module_name,
            "error": str(e),
            "processing_time": processing_time,
            "status": "failed"
        }


def process_package(package_name):
    """Process a package and extract all its modules and functions"""
    logger.info(f"Starting to process package: {package_name}")
    start_time = time.time()

    package_data = {
        "package": package_name,
        "modules": {},
        "timestamp": time.time(),
    }

    try:
        # Get the package
        package = importlib.import_module(package_name)

        # Process the main module
        main_module_data = extract_module_functions(package_name)
        package_data["modules"][package_name] = main_module_data

        # Try to find submodules (this is a best-effort approach)
        if hasattr(package, "__path__"):
            try:
                # This is a simplified version - a more complete solution would use pkgutil.walk_packages
                for _, submodule_name, is_pkg in pkgutil.iter_modules(package.__path__, package_name + "."):
                    if not is_pkg:  # Process only modules, not sub-packages
                        try:
                            submodule_data = extract_module_functions(submodule_name)
                            package_data["modules"][submodule_name] = submodule_data
                        except Exception as e:
                            logger.debug(f"Error processing submodule {submodule_name}: {e}")
            except Exception as e:
                logger.debug(f"Error finding submodules for {package_name}: {e}")
    except Exception as e:
        logger.warning(f"Failed to process package {package_name}: {e}")
        package_data["error"] = str(e)
        package_data["status"] = "failed"

    package_data["processing_time"] = time.time() - start_time
    logger.info(f"Finished processing package {package_name} in {package_data['processing_time']:.2f} seconds")

    return package_data


def store_package_data_mongo(package_data):
    """Store package data in MongoDB"""
    client = get_mongo_client()
    db = client["AutoDS"]
    collection = db["python_functions"]

    # Check if package already exists
    existing = collection.find_one({"package": package_data["package"]})

    if existing:
        # Update existing record
        collection.update_one(
            {"package": package_data["package"]},
            {"$set": package_data}
        )
        logger.info(f"Updated package {package_data['package']} in MongoDB")
    else:
        # Insert new record
        collection.insert_one(package_data)
        logger.info(f"Inserted package {package_data['package']} into MongoDB")

    client.close()


def build_faiss_index(openai_api_key=None):
    """Build FAISS index for all functions in the database"""
    logger.info("Building FAISS index for function search")

    client = get_mongo_client()
    db = client["AutoDS"]
    collection = db["python_functions"]

    # Get all function names with their modules
    all_functions = []

    for package in collection.find():
        package_name = package["package"]

        # Process each module
        for module_name, module_data in package.get("modules", {}).items():
            # Process functions
            for func_name, func_data in module_data.get("functions", {}).items():
                all_functions.append({
                    "id": f"{module_name}.{func_name}",
                    "description": func_data.get("docstring", ""),
                    "signature": func_data.get("signature", "")
                })

            # Process classes and their methods
            for class_name, class_data in module_data.get("classes", {}).items():
                for method_name, method_data in class_data.get("methods", {}).items():
                    all_functions.append({
                        "id": f"{module_name}.{class_name}.{method_name}",
                        "description": method_data.get("docstring", ""),
                        "signature": method_data.get("signature", "")
                    })

    client.close()

    if not all_functions:
        logger.warning("No functions found to index")
        return

    # Generate embeddings
    if openai_api_key:
        logger.info(f"Generating embeddings for {len(all_functions)} functions")

        # Initialize OpenAI client
        openai_client = OpenAI(api_key=openai_api_key)

        # Prepare texts for embedding
        function_texts = [
            f"{func['id']}\n{func['signature']}\n{func['description']}"
            for func in all_functions
        ]

        # Generate embeddings in batches
        batch_size = 100
        embeddings = []

        for i in range(0, len(function_texts), batch_size):
            batch = function_texts[i:i + batch_size]
            logger.info(
                f"Processing embedding batch {i // batch_size + 1}/{(len(function_texts) + batch_size - 1) // batch_size}")

            try:
                response = openai_client.embeddings.create(
                    input=batch,
                    model="text-embedding-ada-002"
                )

                batch_embeddings = [np.array(item.embedding) for item in response.data]
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
                return

        # Create and save the index
        if embeddings:
            embeddings_array = np.array(embeddings).astype('float32')
            dimension = embeddings_array.shape[1]

            # Create FAISS index
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings_array)

            # Save index and function IDs
            faiss.write_index(index, "function_index.bin")
            with open("function_ids.json", "w") as f:
                json.dump([func["id"] for func in all_functions], f)

            logger.info(f"FAISS index created with {len(embeddings)} functions")
        else:
            logger.warning("No embeddings generated")
    else:
        logger.warning("OpenAI API key not provided, skipping embedding generation")


def main():
    """Main function to orchestrate the database expansion"""
    logger.info("Starting AutoDS database expansion")

    # Get packages to process
    packages = get_top_pypi_packages(120)
    logger.info(f"Found {len(packages)} packages to process")

    # Process packages in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_package = {
            executor.submit(process_package, package): package
            for package in packages
        }

        for i, future in enumerate(future_to_package):
            package = future_to_package[future]
            try:
                package_data = future.result()
                store_package_data_mongo(package_data)
                logger.info(f"[{i + 1}/{len(packages)}] Processed {package}")
            except Exception as e:
                logger.error(f"Error processing {package}: {e}")

    # Build FAISS index
    build_faiss_index(openai_api_key=OPENAI_API_KEY)

    logger.info("Database expansion completed")


if __name__ == "__main__":
    import pkgutil  # Import here to avoid potential issues

    main()