#!/usr/bin/env python3
"""
main.py - AutoDS CLI Interface
"""

import sys
import os
import json
import logging
from colorama import init, Fore, Style

# Add the src directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(script_dir, "src"))

# Now import the agent
from agent.agent import process_query

# Initialize colorama
init(autoreset=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("autods.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AutoDS")


def print_header():
    """Print a fancy header for the CLI"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Fore.CYAN}╔═══════════════════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║ {Fore.WHITE}                      AutoDS                        {Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║ {Fore.WHITE}  Auto-Generating AI Agent for Python/R Functions   {Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}╚═══════════════════════════════════════════════════════╝{Style.RESET_ALL}")
    print()
    print(f"{Fore.WHITE}Tell me what data science task you'd like to perform,")
    print(f"and I'll find and run the right function for you.{Style.RESET_ALL}")
    print()
    print(f"{Fore.YELLOW}Type 'exit' to quit, 'help' for more information.{Style.RESET_ALL}")
    print()


def print_help():
    """Print help information"""
    print(f"\n{Fore.GREEN}=== AutoDS Help ===={Style.RESET_ALL}")
    print("\nExample queries:")
    print(f"  {Fore.CYAN}* Train a decision tree on my dataset{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}* Perform linear regression{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}* Cluster my data into groups{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}* Calculate correlation between variables{Style.RESET_ALL}")

    print("\nArgument format:")
    print("  Provide arguments as a JSON object. Examples:")
    print(f"  {Fore.YELLOW}{{\"data\": [[1,2], [2,3], [3,4]], \"n_clusters\": 3}}{Style.RESET_ALL}")
    print(f"  {Fore.YELLOW}{{\"formula\": \"y ~ x\", \"data\": \"mtcars\"}}{Style.RESET_ALL}")

    print("\nBuilt-in R datasets you can use:")
    print(f"  {Fore.YELLOW}mtcars, iris, ToothGrowth, airquality{Style.RESET_ALL}")

    print("\nCommands:")
    print(f"  {Fore.GREEN}help{Style.RESET_ALL} - Show this help information")
    print(f"  {Fore.GREEN}clear{Style.RESET_ALL} - Clear the screen")
    print(f"  {Fore.GREEN}debug{Style.RESET_ALL} - Toggle debug mode (shows more information)")
    print(f"  {Fore.GREEN}examples{Style.RESET_ALL} - Show specific examples for common tasks")
    print(f"  {Fore.GREEN}exit{Style.RESET_ALL} - Exit the application")
    print()


def print_examples():
    """Print specific examples for common tasks"""
    print(f"\n{Fore.GREEN}=== AutoDS Examples ===={Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}Linear Regression{Style.RESET_ALL}")
    print("  Query: perform linear regression")
    print(f"  Args:  {Fore.YELLOW}{{\"formula\": \"y ~ x\", \"data\": [[1,2], [2,3], [3,4]]}}{Style.RESET_ALL}")
    print("  Alternative Args with R dataset:")
    print(f"  Args:  {Fore.YELLOW}{{\"formula\": \"mpg ~ wt\", \"data\": \"mtcars\"}}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}T-Test{Style.RESET_ALL}")
    print("  Query: perform t-test")
    print(f"  Args:  {Fore.YELLOW}{{\"x\": [1,2,3,4,5], \"y\": [2,3,4,5,6]}}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}Correlation{Style.RESET_ALL}")
    print("  Query: calculate correlation")
    print(f"  Args:  {Fore.YELLOW}{{\"x\": [[1,2,3], [4,5,6], [7,8,9]]}}{Style.RESET_ALL}")

    print()


def handle_linear_regression():
    """Special handler for linear regression to ensure it works properly"""
    print(f"\n{Fore.CYAN}Linear Regression Assistant{Style.RESET_ALL}")
    print("This will help you perform linear regression analysis.")

    # Get formula
    print(f"\n{Fore.YELLOW}Enter your formula (e.g., 'y ~ x' or 'mpg ~ wt'):{Style.RESET_ALL}")
    formula = input(f"{Fore.GREEN}Formula>{Style.RESET_ALL} ")

    if not formula.strip():
        formula = "y ~ x"
        print(f"{Fore.YELLOW}Using default formula: {formula}{Style.RESET_ALL}")

    # Get data
    print(f"\n{Fore.YELLOW}Choose data option:{Style.RESET_ALL}")
    print(f"  1) Use built-in R dataset (mtcars, iris, etc.)")
    print(f"  2) Enter your own x,y pairs")

    data_choice = input(f"{Fore.GREEN}Option (1/2)>{Style.RESET_ALL} ")

    if data_choice == "1":
        print(f"\n{Fore.YELLOW}Enter dataset name (mtcars, iris, ToothGrowth, airquality):{Style.RESET_ALL}")
        dataset = input(f"{Fore.GREEN}Dataset>{Style.RESET_ALL} ")

        if not dataset.strip() in ["mtcars", "iris", "ToothGrowth", "airquality"]:
            dataset = "mtcars"
            print(f"{Fore.YELLOW}Using default dataset: {dataset}{Style.RESET_ALL}")

        args = {"formula": formula, "data": dataset}
    else:
        print(
            f"\n{Fore.YELLOW}Enter x,y pairs as comma-separated values (one pair per line, blank line to finish):{Style.RESET_ALL}")
        print(f"Example: 1,2 (meaning x=1, y=2)")

        data_pairs = []
        while True:
            line = input(f"{Fore.GREEN}Point>{Style.RESET_ALL} ")
            if not line.strip():
                break

            try:
                values = [float(v.strip()) for v in line.split(",")]
                if len(values) == 2:
                    data_pairs.append(values)
                else:
                    print(f"{Fore.RED}Error: Need exactly 2 values per line. Try again.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Error: Invalid number format. Try again.{Style.RESET_ALL}")

        if not data_pairs:
            # Default data if user didn't enter any
            data_pairs = [[1, 2], [2, 3], [3, 4]]
            print(f"{Fore.YELLOW}Using default data points: {data_pairs}{Style.RESET_ALL}")

        args = {"formula": formula, "data": data_pairs}

    # Execute the query
    print(f"\n{Fore.CYAN}Processing linear regression...{Style.RESET_ALL}")
    result = process_query("perform linear regression", args)

    # Display results
    if result["success"]:
        print(f"\n{Fore.GREEN}✓ Linear regression executed successfully!{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Code:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{result['code_snippet']}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Result:{Style.RESET_ALL}")
        print(result["result"])
    else:
        print(f"\n{Fore.RED}✗ Error executing linear regression:{Style.RESET_ALL}")
        print(result["error"])

        print(f"\n{Fore.YELLOW}Traceback:{Style.RESET_ALL}")
        print(result.get("traceback", "No traceback available"))

    print()
    return


def main():
    """Main CLI interface for AutoDS"""
    logger.info("Starting AutoDS CLI interface")
    debug_mode = False
    print_header()

    while True:
        try:
            user_query = input(f"{Fore.GREEN}AutoDS>{Style.RESET_ALL} ")

            # Handle special commands
            if user_query.lower() == "exit":
                break
            elif user_query.lower() == "help":
                print_help()
                continue
            elif user_query.lower() == "clear":
                print_header()
                continue
            elif user_query.lower() == "debug":
                debug_mode = not debug_mode
                print(f"{Fore.YELLOW}Debug mode {'enabled' if debug_mode else 'disabled'}{Style.RESET_ALL}")
                continue
            elif user_query.lower() == "examples":
                print_examples()
                continue
            elif user_query.lower() in ["lr", "linear", "regression", "linear regression"]:
                handle_linear_regression()
                continue
            elif not user_query.strip():
                continue

            # Ask for parameters
            print(f"\n{Fore.YELLOW}Enter function arguments as JSON (or press Enter for none):{Style.RESET_ALL}")
            args_json = input(f"{Fore.GREEN}Args>{Style.RESET_ALL} ")

            try:
                args = json.loads(args_json) if args_json.strip() else {}
            except json.JSONDecodeError:
                print(f"{Fore.RED}Invalid JSON format. Using empty arguments.{Style.RESET_ALL}")
                args = {}

            print(f"\n{Fore.CYAN}Processing your request...{Style.RESET_ALL}")

            # Process the query
            result = process_query(user_query, args)

            if result["success"]:
                print(f"\n{Fore.GREEN}✓ Function executed successfully!{Style.RESET_ALL}")
                print(f"\n{Fore.YELLOW}Language:{Style.RESET_ALL} {result.get('language', 'unknown')}")
                print(f"\n{Fore.YELLOW}Code:{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{result['code_snippet']}{Style.RESET_ALL}")
                print(f"\n{Fore.YELLOW}Result:{Style.RESET_ALL}")
                print(result["result"])
            else:
                print(f"\n{Fore.RED}✗ Error executing function:{Style.RESET_ALL}")
                print(result["error"])

                # Print traceback in debug mode
                if debug_mode and "traceback" in result:
                    print(f"\n{Fore.YELLOW}Traceback:{Style.RESET_ALL}")
                    print(result["traceback"])
                elif "traceback" in result and not debug_mode:
                    print(f"\n{Fore.YELLOW}Use 'debug' command to see the full error traceback{Style.RESET_ALL}")

                # Special handling for common queries
                if "linear regression" in user_query.lower():
                    print(f"\n{Fore.YELLOW}It seems you're trying to perform linear regression.{Style.RESET_ALL}")
                    print(f"Try using the built-in linear regression assistant by typing 'lr' or 'linear regression'.")

                # Provide helpful suggestions
                print(f"\n{Fore.YELLOW}Suggestions:{Style.RESET_ALL}")
                print("- Check if the arguments match the function requirements")
                print("- Try a more specific query (e.g., 'stats linear regression')")
                print("- Verify the data format is correct")
                print("- For R functions, try using built-in datasets like 'mtcars' or 'iris'")

            print()  # Add a blank line for readability

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            if debug_mode:
                import traceback
                print(f"\n{Fore.YELLOW}Traceback:{Style.RESET_ALL}")
                print(traceback.format_exc())
            logger.error(f"Error in CLI: {e}")

    logger.info("AutoDS CLI interface closed")
    print(f"{Fore.YELLOW}Thank you for using AutoDS!{Style.RESET_ALL}")


if __name__ == "__main__":
    main()