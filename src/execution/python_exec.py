#!/usr/bin/env python3
import importlib
import traceback

def execute_python_function(function_details, args):
    """
    Dynamically import a Python module and execute the specified function
    with given arguments.
    """
    try:
        package_name = function_details["package"]
        function_name = function_details["function_name"]

        # Import the module and get the function object
        module = importlib.import_module(package_name)
        func = getattr(module, function_name)

        # Execute the function with provided arguments
        result = func(**args)

        return {
            "success": True,
            "result": result
        }
    except Exception as e:
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