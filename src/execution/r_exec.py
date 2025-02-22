import rpy2.robjects as robjects
import traceback

def execute_r_function(function_details, args):
    """
    Executes an R function dynamically using rpy2.

    :param function_details: Dictionary containing function metadata (package, function_name).
    :param args: Dictionary containing the function arguments (e.g., {"formula": ..., "data": ...}).
    :return: Execution result or error message.
    """
    try:
        # Load the R package
        robjects.r(f'library({function_details["package"]})')
        r_function = robjects.r[function_details["function_name"]]

        # Prepare arguments as a dictionary
        r_args = {}

        # Handle 'formula' argument (pass as string, R will convert it)
        if "formula" in args:
            r_args["formula"] = args["formula"]

        # Handle 'data' argument (convert nested list to R data frame)
        if "data" in args and isinstance(args["data"], list):
            data = args["data"]
            r_args["data"] = robjects.DataFrame({
                "x": robjects.FloatVector([row[0] for row in data]),
                "y": robjects.FloatVector([row[1] for row in data])
            })

        # Execute the function with named arguments
        result = r_function(**r_args)

        # Convert the R result to a Python-friendly dictionary
        return {"success": True, "result": dict(result.items())}

    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}