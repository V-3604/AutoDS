#!/usr/bin/env python3
import traceback
import rpy2.robjects as robjects
from rpy2.robjects import vectors as rvectors
import logging
import numpy as np

# Setup logging
logger = logging.getLogger("AutoDS")


def execute_r_function(function_details, args):
    """
    Dynamically load an R package and call the specified function
    with given arguments using rpy2.
    """
    try:
        package_name = function_details["package"]
        function_name = function_details["function_name"]

        logger.info(f"Executing R function: {package_name}::{function_name}")
        logger.info(f"Arguments: {args}")

        # Load the required R package
        try:
            robjects.r(f"library({package_name})")
        except Exception as e:
            logger.error(f"Error loading R package {package_name}: {e}")
            return {
                "success": False,
                "error": f"Failed to load R package '{package_name}': {e}"
            }

        try:
            r_func = robjects.r[function_name]
        except Exception as e:
            logger.error(f"Error accessing R function {function_name}: {e}")
            return {
                "success": False,
                "error": f"Function '{function_name}' not found in package '{package_name}': {e}"
            }

        # Convert Python arguments into R-compatible objects
        r_args = {}
        for key, value in args.items():
            logger.info(f"Processing argument '{key}' of type {type(value)}")

            if key.lower() == "formula" and isinstance(value, str):
                # Handle formula expression
                try:
                    r_args[key] = robjects.Formula(value)
                    logger.info(f"Converted '{key}' to R formula: {value}")
                except Exception as e:
                    logger.error(f"Error converting formula '{value}': {e}")
                    r_args[key] = value

            elif isinstance(value, list):
                # Special handling for linear regression data which is often a list of lists
                if all(isinstance(row, list) for row in value):
                    # Convert list of lists to R matrix or data frame
                    try:
                        # Convert to numpy array first for easier handling
                        data_array = np.array(value)

                        # Create matrix using R matrix function
                        r_vector = rvectors.FloatVector(data_array.flatten())
                        r_matrix = robjects.r['matrix'](r_vector,
                                                        nrow=data_array.shape[0],
                                                        ncol=data_array.shape[1])

                        # For linear regression, convert to data frame with named columns
                        if function_name == "lm":
                            if data_array.shape[1] == 2:
                                # Typical x,y data
                                df = robjects.r['data.frame'](
                                    x=rvectors.FloatVector(data_array[:, 0]),
                                    y=rvectors.FloatVector(data_array[:, 1])
                                )
                                r_args[key] = df
                                logger.info(f"Converted '{key}' to R data frame with x,y columns")
                            else:
                                # Multi-column data
                                col_dict = {}
                                for i in range(data_array.shape[1]):
                                    col_dict[f"col{i}"] = rvectors.FloatVector(data_array[:, i])
                                df = robjects.r['data.frame'](**col_dict)
                                r_args[key] = df
                                logger.info(f"Converted '{key}' to R data frame with {data_array.shape[1]} columns")
                        else:
                            # For other functions, use the matrix as is
                            r_args[key] = r_matrix
                            logger.info(f"Converted '{key}' to R matrix with shape {data_array.shape}")
                    except Exception as e:
                        logger.error(f"Error converting matrix data: {e}")
                        # Fallback to simpler method
                        r_cmd = "rbind("
                        for row in value:
                            r_cmd += f"c({','.join(str(x) for x in row)}),"
                        r_cmd = r_cmd.rstrip(',') + ")"

                        try:
                            r_matrix = robjects.r(r_cmd)
                            r_args[key] = r_matrix
                            logger.info(f"Fallback: Converted '{key}' to R matrix using rbind")
                        except Exception as e2:
                            logger.error(f"Fallback conversion also failed: {e2}")
                            r_args[key] = value
                else:
                    # It's a simple list, convert to R vector
                    try:
                        if all(isinstance(x, (int, float)) for x in value):
                            r_args[key] = rvectors.FloatVector(value)
                            logger.info(f"Converted '{key}' to R numeric vector of length {len(value)}")
                        else:
                            r_args[key] = rvectors.StrVector([str(x) for x in value])
                            logger.info(f"Converted '{key}' to R string vector of length {len(value)}")
                    except Exception as e:
                        logger.error(f"Error converting vector: {e}")
                        r_args[key] = value

            elif isinstance(value, str) and value.strip() in ["mtcars", "iris", "ToothGrowth", "airquality"]:
                # Handle R built-in datasets
                try:
                    r_args[key] = robjects.r(value)
                    logger.info(f"Using R built-in dataset: {value}")
                except Exception as e:
                    logger.error(f"Error loading R dataset '{value}': {e}")
                    r_args[key] = value
            else:
                # Pass other values as is
                r_args[key] = value
                logger.info(f"Using '{key}' value as is: {value}")

        # Call the R function with the prepared arguments
        logger.info(f"Calling R function with arguments: {r_args}")

        try:
            result = r_func(**r_args)

            # For linear model results, extract coefficients for better display
            if function_name == "lm":
                try:
                    # Store the model in R environment
                    robjects.r.assign("model", result)

                    # Get summary and coefficients
                    summary = robjects.r("summary(model)")
                    coef = robjects.r("coef(summary(model))")
                    intercept = robjects.r("coef(model)[1]")
                    slope = robjects.r("if(length(coef(model)) > 1) coef(model)[2] else NA")

                    # Format the output as a readable string
                    result_str = f"Linear Regression Results:\n\n"
                    result_str += f"Formula: {args.get('formula', 'y ~ x')}\n\n"
                    result_str += f"Coefficients:\n"
                    result_str += f"  (Intercept): {float(intercept[0]):.4f}\n"

                    if str(slope[0]) != "NA":
                        result_str += f"  x: {float(slope[0]):.4f}\n\n"

                    result_str += f"Summary:\n{str(coef)}"

                    return {
                        "success": True,
                        "result": result_str
                    }
                except Exception as e:
                    logger.warning(f"Error getting detailed model output: {e}")
                    # Fall back to basic output
                    return {
                        "success": True,
                        "result": str(result)
                    }
            else:
                return {
                    "success": True,
                    "result": str(result)
                }

        except Exception as e:
            logger.error(f"Error calling R function: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": f"Error calling R function: {str(e)}",
                "traceback": traceback.format_exc()
            }

    except Exception as e:
        logger.error(f"Error in R execution: {e}")
        logger.error(traceback.format_exc())
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
        "formula": "y ~ x",
        "data": [
            [1, 1.2],
            [2, 2.3],
            [3, 3.5],
            [4, 4.1]
        ]
    }
    output = execute_r_function(function_details, args)
    print(output)