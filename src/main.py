#!/usr/bin/env python3
"""
main.py (updated)
"""

import sys
import os
import json
import logging
from colorama import init, Fore, Style

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

# Now import the agent
from agent.agent import process_query

# Initialize colorama
init()

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

    print("\nCommands:")
    print(f"  {Fore.GREEN}help{Style.RESET_ALL} - Show this help information")
    print(f"  {Fore.GREEN}clear{Style.RESET_ALL} - Clear the screen")
    print(f"  {Fore.GREEN}exit{Style.RESET_ALL} - Exit the application")
    print()


def main():
    """Main CLI interface for AutoDS"""
    logger.info("Starting AutoDS CLI interface")
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

                # Print traceback if available
                if "traceback" in result:
                    print(f"\n{Fore.YELLOW}Traceback:{Style.RESET_ALL}")
                    print(result["traceback"])

                # Provide helpful suggestions
                print(f"\n{Fore.YELLOW}Suggestions:{Style.RESET_ALL}")
                print("- Check if the arguments match the function requirements")
                print("- Try a more specific query")
                print("- Verify the data format is correct")

            print()  # Add a blank line for readability

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Exiting...{Style.RESET_ALL}")
            break
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            logger.error(f"Error in CLI: {e}")

    logger.info("AutoDS CLI interface closed")
    print(f"{Fore.YELLOW}Thank you for using AutoDS!{Style.RESET_ALL}")


if __name__ == "__main__":
    main()