from src.agent.agent import process_query
import json

# Rest of the code remains unchanged
def main():
    while True:
        user_query = input("Enter a command (or 'exit' to quit): ")
        if user_query.lower() == "exit":
            break

        # Ask for parameters
        args_json = input("Enter function arguments as JSON: ")
        try:
            args = json.loads(args_json)
        except json.JSONDecodeError:
            print("Invalid JSON format.")
            continue

        # Process the query
        result = process_query(user_query, args)
        print("Result:", result)

if __name__ == "__main__":
    main()
