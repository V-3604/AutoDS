#!/usr/bin/env python3
"""
rebuild_autods.py - Complete rebuild of the AutoDS system
"""

import os
import sys
import logging
import subprocess
import time
from pymongo import MongoClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("autods_rebuild.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AutoDS")


def check_mongodb():
    """Check if MongoDB is running and accessible"""
    logger.info("Checking MongoDB connection...")
    try:
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
        client.server_info()  # Will raise exception if connection fails
        logger.info("✓ MongoDB is running and accessible")
        return True
    except Exception as e:
        logger.error(f"✗ MongoDB connection failed: {e}")
        logger.error("Please make sure MongoDB is running on localhost:27017")
        return False


def run_command(command, description):
    """Run a shell command and log the output"""
    logger.info(f"Running: {description}")
    logger.info(f"Command: {command}")

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            universal_newlines=True
        )

        stdout, stderr = process.communicate()

        if process.returncode == 0:
            logger.info(f"✓ {description} completed successfully")
            if stdout:
                logger.info(stdout)
            return True
        else:
            logger.error(f"✗ {description} failed with return code {process.returncode}")
            if stderr:
                logger.error(stderr)
            return False
    except Exception as e:
        logger.error(f"✗ Error running {description}: {e}")
        return False


def setup_autods():
    """Set up and rebuild the entire AutoDS system"""
    start_time = time.time()
    logger.info("Starting complete AutoDS setup and rebuild...")

    # First check MongoDB
    if not check_mongodb():
        logger.error("MongoDB check failed. Exiting.")
        return False

    # Run the directory setup script
    if not run_command("python scripts/create_directory_structure.py", "Directory structure setup"):
        logger.warning("Directory setup had issues but continuing...")

    # Run the Python function scraper
    if not run_command("python scripts/python_function_scraper.py", "Python function scraper"):
        logger.error("Python function scraper failed. Exiting.")
        return False

    # Run the R function scraper - make it optional
    r_result = run_command("Rscript scripts/r_function_scraper.R", "R function scraper")
    if not r_result:
        logger.warning("R function scraper failed. Continuing with Python only.")

    # Run the database unification
    if not run_command("python scripts/unify_database.py", "Database unification"):
        logger.error("Database unification failed. Exiting.")
        return False

    # Build the vector store
    if not run_command("python src/vector/vector_store.py", "Vector store builder"):
        logger.error("Vector store build failed. Exiting.")
        return False

    # Test a linear regression query
    logger.info("Testing linear regression query...")
    test_cmd = """
    python -c "
import sys, os, json
sys.path.append(os.path.join(os.path.dirname(os.path.abspath('.')), 'src'))
from agent.agent import process_query
result = process_query('perform linear regression', {'formula': 'y ~ x', 'data': [[1,2], [2,3], [3,4]]})
print(json.dumps(result, indent=2))
"
    """
    run_command(test_cmd, "Testing linear regression query")

    elapsed_time = time.time() - start_time
    logger.info(f"✓ AutoDS rebuild completed in {elapsed_time:.2f} seconds")
    logger.info("You can now run 'python main.py' to start the AutoDS CLI")

    return True


if __name__ == "__main__":
    setup_autods()