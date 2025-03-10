#!/usr/bin/env python3
"""
create_directory_structure.py - Create necessary directory structure for AutoDS
"""
import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutoDS")


def create_directory_structure():
    """Create the necessary directory structure for AutoDS"""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Define required directories
    directories = [
        os.path.join(base_dir, 'src'),
        os.path.join(base_dir, 'src', 'agent'),
        os.path.join(base_dir, 'src', 'execution'),
        os.path.join(base_dir, 'src', 'vector'),
        os.path.join(base_dir, 'src', 'vector', 'vectors'),
        os.path.join(base_dir, 'scripts')
    ]

    # Create directories
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

    # Create __init__.py files in each directory
    init_files = [
        os.path.join(base_dir, 'src', '__init__.py'),
        os.path.join(base_dir, 'src', 'agent', '__init__.py'),
        os.path.join(base_dir, 'src', 'execution', '__init__.py'),
        os.path.join(base_dir, 'src', 'vector', '__init__.py')
    ]

    for init_file in init_files:
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("# AutoDS module initialization file\n")
            logger.info(f"Created: {init_file}")

    logger.info("Directory structure created successfully")
    return True


if __name__ == "__main__":
    create_directory_structure()