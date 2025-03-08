#!/usr/bin/env python3
import traceback
import rpy2.robjects as robjects
from rpy2.robjects import vectors as rvectors

def execute_r_function(function_details, args):
    """
    Dynamically load an R package and call the specified function
    with given arguments using rpy2.
    """
    try:
        package_name = function_details["package"]
        function_name = function_details["function_name"]

        # Load the required R package
        robjects.r(f"library({package_name})")
        r_func = robjects.r[function_name]

        # Convert Python arguments into R-compatible objects
        r_args = {}
        for key, value in args.items():
            if isinstance(value, list):
                # Handle lists of lists as data frames; otherwise, use vectors
                if all(isinstance(row, list) for row in value):
                    df_dict = {}
                    num_cols = len(value[0])
                    for col_idx in range(num_cols):
                        col_name = f"col{col_idx}"
                        col_vals = [row[col_idx] for row in value]
                        if all(isinstance(item, (int, float)) for item in col_vals):
                            df_dict[col_name] = rvectors.FloatVector(col_vals)
                        else:
                            df_dict[col_name] = rvectors.StrVector(str(x) for x in col_vals)
                    r_args[key] = robjects.DataFrame(df_dict)
                else:
                    if all(isinstance(x, (int, float)) for x in value):
                        r_args[key] = rvectors.FloatVector(value)
                    else:
                        r_args[key] = rvectors.StrVector(str(x) for x in value)
            else:
                # If it's a formula in string format, convert it
                if key.lower() == "formula" and isinstance(value, str):
                    r_args[key] = robjects.Formula(value)
                else:
                    r_args[key] = value

        # Call the R function with the prepared arguments
        result = r_func(**r_args)
        return {
            "success": True,
            "result": str(result)
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
        "package": "stats",
        "function_name": "lm"
    }
    args = {
        "formula": "col1 ~ col0",
        "data": [
            [1, 1.2],
            [2, 2.3],
            [3, 3.5],
            [4, 4.1]
        ]
    }
    output = execute_r_function(function_details, args)
    print(output)