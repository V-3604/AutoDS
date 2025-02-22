import importlib
import json
import traceback


def execute_python_function(function_details, args):
    """
    Executes a Python function dynamically.

    :param function_details: Dictionary containing function metadata (package, function_name).
    :param args: Dictionary containing the function arguments.
    :return: Execution result or error message.
    """
    try:
        # Import the required module dynamically
        module = importlib.import_module(function_details["package"])

        # Get the function from the module
        func = getattr(module, function_details["function_name"])

        # Execute the function with arguments
        result = func(**args)
        return {"success": True, "result": result}

    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
