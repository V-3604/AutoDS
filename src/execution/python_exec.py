#!/usr/bin/env python3
import importlib
import traceback
import logging

# Setup logging
logger = logging.getLogger("AutoDS")


def execute_python_function(function_details, args):
    """
    Dynamically import a Python module and execute the specified function
    with given arguments.
    """
    try:
        package_name = function_details["package"]
        function_name = function_details["function_name"]

        logger.info(f"Executing Python function: {package_name}.{function_name}")
        logger.info(f"With arguments: {args}")

        # Import the module and get the function object
        try:
            module = importlib.import_module(package_name)
        except ImportError as e:
            logger.error(f"Failed to import module {package_name}: {e}")
            return {
                "success": False,
                "error": f"Failed to import module {package_name}: {e}",
                "traceback": traceback.format_exc()
            }

        # Try to get the function from the module
        try:
            # Handle cases where function might be in a submodule or class
            if '.' in function_name:
                parts = function_name.split('.')
                obj = module
                for part in parts:
                    obj = getattr(obj, part)
                func = obj
            else:
                func = getattr(module, function_name)

            logger.info(f"Successfully found function {function_name} in module {package_name}")
        except AttributeError as e:
            logger.error(f"Function {function_name} not found in module {package_name}: {e}")
            return {
                "success": False,
                "error": f"module '{package_name}' has no attribute '{function_name}'",
                "traceback": traceback.format_exc()
            }

        # Execute the function with provided arguments
        logger.info(f"Calling function with arguments: {args}")
        try:
            result = func(**args)
            logger.info(f"Function executed successfully")
            return {
                "success": True,
                "result": str(result)
            }
        except Exception as e:
            logger.error(f"Error executing function: {e}")
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    except Exception as e:
        logger.error(f"Unexpected error in execute_python_function: {e}")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


# Optional local test
if __name__ == "__main__":
    function_details = {
        "package": "math",
        "function_name": "sqrt"
    }
    args = {"x": 16}
    output = execute_python_function(function_details, args)
    print(output)