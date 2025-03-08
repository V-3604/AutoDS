AutoDS - Automated Data Science Assistant

Project Overview

AutoDS is an AI-driven assistant that helps users perform data science tasks without manually coding functions. It interprets natural language queries (e.g. "Train a decision tree on my dataset") and automatically finds an appropriate function from a library of Python or R data science packages to execute the task. The system leverages a database of functions scraped from popular libraries and uses semantic search to match user requests to the right function. By automating function selection and execution, AutoDS aims to streamline workflows for data analysis and machine learning tasks. How it works: AutoDS maintains a knowledge base of functions (from packages like NumPy, pandas, scikit-learn in Python, and stats, rpart, etc. in R). When you enter a query, the system obtains a text embedding of the query and searches for the most relevant function in its database. Once a suitable function is identified, AutoDS will generate a code snippet showing how the function is called, execute the function with the provided arguments, and return the results — all within a single interactive session.
Current Functionality

AutoDS is in an early development stage, and several core features are already implemented and working:
Interactive CLI Interface: AutoDS provides a command-line prompt with colored text and a simple menu. Users can type natural language queries, get prompted for parameters (in JSON format), and see results directly in the terminal. Commands like help, clear, and exit are available for guidance and convenience.
Semantic Query Matching: The system uses OpenAI embeddings and a FAISS vector index to interpret user queries. It compares the query against a catalog of function descriptions to find the best match. This enables more flexible, semantic matching (e.g. a query "perform linear regression" can match a function stats::lm in R or sklearn.linear_model.LinearRegression in Python based on description).
Multi-Language Function Support: AutoDS can utilize both Python and R functions. It has a knowledge base of functions from popular Python libraries (NumPy, pandas, SciPy, scikit-learn, XGBoost, LightGBM, etc.) and R packages (stats, rpart, randomForest, e1071, cluster, glmnet, MASS). The system decides whether a Python or R function is more relevant to the query and can execute either.
Automated Function Execution: Once a function is selected, AutoDS will execute the function automatically. For Python functions, it uses dynamic importing (importlib) to load the module and call the function. For R functions, it relies on rpy2 to call R functions within the Python process. The user-provided arguments (if any) are passed into the function call.
Result Display and Transparency: After execution, the CLI displays a success message along with the detected language, the code snippet that was run, and the result of the function. This gives users transparency into what was executed. For example, if you ask for correlation, it might show a snippet like import numpy; numpy.corrcoef(data) and print the numeric result.
Basic Error Handling: The system catches exceptions during execution and reports errors without crashing. If a function call fails, AutoDS will display an error message, the exception traceback (for debugging), and some suggestions (e.g. checking argument formats or trying a more specific query). This helps users adjust their query or inputs when something goes wrong.
Function Database and Logging: A MongoDB-backed database (AutoDS database with collections for Python and R functions) stores metadata about each scraped function (name, package, parameters, documentation snippet, etc.). These entries are unified into a single functions_catalog used for search. The system logs key events (queries, matches, errors) to a log file (autods.log) for debugging and analysis.
In summary, AutoDS currently functions as a CLI-based intelligent agent that can understand a user’s data science request, identify an appropriate pre-existing function, execute it behind the scenes, and return the outcome. This can save time for users who know what they want to do but prefer the tool to figure out the exact function and syntax.
Limitations and Bugs

Despite the promising functionality, there are several limitations and known issues in the current version of AutoDS:
Manual Database Setup: The function knowledge base is not bundled by default – it must be built by running scraper scripts. If the database or index is not prepared, AutoDS may not find any function for a query (or could error due to missing index). There is no built-in prompt to guide the user to set this up, so first-time users might encounter a “No matching function found” message until the database is initialized.
Complex Setup Requirements: AutoDS depends on external services and environments – it requires a running MongoDB server for the function catalog, and an OpenAI API key for embedding generation. Without an OpenAI API key, the semantic search will not function (currently, the code will raise an exception if the key is missing). Similarly, R functionality requires R and the rpy2 Python package to be properly installed. These dependencies mean the environment must be configured correctly, which can be a barrier for some users.
Parameter Input Handling: The CLI expects function arguments to be provided as a JSON object. This is functional (and allows complex data structures), but not very user-friendly for non-programmers. An incorrectly formatted JSON will be rejected with an error. Moreover, the system’s ability to infer or supply default arguments is limited. If the user does not provide a required parameter, the function call will likely fail. Currently, the agent only auto-fills certain cases (e.g. an R function requiring a data frame will default to the iris dataset if no data is given), but most parameters are not auto-inferred. This means the user must know what arguments a function needs in many cases.
Schema Mismatch for Function Metadata: There is a minor bug in how function parameters are stored and used for inference between Python and R entries. Python function metadata in the database includes a detailed parameters list (with names, defaults, etc.), whereas R function metadata stores an arguments list of name/default pairs. The unified catalog doesn’t consistently translate these – for Python functions, the arguments field is often empty, and for R functions, the defaults field is empty. This can confuse the infer_parameters logic. For example, the agent might treat all R function arguments as required (since it doesn’t see default values), potentially causing execution errors or unnecessary prompts. This is a known issue that requires adjusting how the metadata is unified or interpreted.
Limited Query Understanding: The semantic search is based purely on embedding similarity of the function descriptions. While this is powerful, it might occasionally pick a less-than-ideal function if the descriptions are vague or if multiple functions are similar. The system does not currently ask the user to confirm or choose among multiple matches – it always executes the top match. If that match isn’t what the user intended, the user has to rephrase the query manually. There’s no interactive disambiguation or query refinement step.
Output Limitations: AutoDS simply prints the result of the function call. If the result is a complex object (like a model object or a large matrix), the display may not be nicely formatted. Also, if the function produces a plot or GUI (common in data science tasks), those won’t be visible through this CLI interface. For example, asking for a scatter plot might execute the code, but without a graphical backend in CLI, the plot will not be shown to the user.
Hard-Coded Paths and Configs: The R scraping script currently has a hard-coded file path for installing packages and logging (pointing to a specific user’s directory). This is a bug that will affect other users running the scraper on their machines. It needs to be changed to a relative path or configurable directory. Until this is fixed, running the R scraper as-is will attempt to write to a non-existent directory.
No GUI or Notebook Integration: As of now, AutoDS runs purely in the terminal. There is no web interface or Jupyter notebook integration. All interactions are text-based. This is acceptable for many use cases, but a richer interface could improve user experience in the future.
Lack of Unit Tests: The project does not appear to include automated tests. The reliability has been observed through manual testing, but certain edge cases might not have been covered. For instance, functions that require special data types or environment (like a connection or a file) may not be handled gracefully.
Overall, the system is a proof-of-concept and works for straightforward data science queries with standard libraries, but it requires careful setup and has rough edges in error handling and flexibility. Users should be aware of these limitations and be prepared to do some troubleshooting or setup adjustments.
Installation Guide

Prerequisites: Before installing and running AutoDS, ensure you have the following installed on your system:
Python 3.x (developed and tested on Python 3; required for the AutoDS CLI and scrapers).
R (preferably R 4.x) and the command-line tool Rscript (required if you plan to include R functions in the database and use R execution).
MongoDB (community edition is fine, running locally on the default port 27017. AutoDS uses MongoDB as its database to store function metadata).
OpenAI API Key (needed for semantic search embeddings. You can get one by signing up at OpenAI. Set this key as an environment variable or in a .env file in the project directory as OPENAI_API_KEY="your-key-here").
Python Dependencies: The main Python packages required are:
pymongo (for MongoDB interactions)
faiss-cpu (Facebook AI Similarity Search for the vector index)
openai (OpenAI API client for embeddings)
python-dotenv (to load environment variables from a .env file)
colorama (for colored CLI text output)
rpy2 (for calling R from Python)
numpy (used in embedding handling and possibly required for certain functions)
requests, matplotlib, seaborn, scipy, sklearn, etc. (the scraper will attempt to install many common data science libraries; ensure you have a C/C++ build environment if needed for some packages like SciPy).
These can be installed via pip. If a requirements.txt is provided, run:
pip install -r requirements.txt
Otherwise, install manually:
pip install pymongo faiss-cpu openai python-dotenv colorama rpy2 numpy
(Note: the python_function_scraper.py script can automatically pip-install the needed data science packages it plans to scrape, so you don't necessarily need to manually install pandas, scikit-learn, etc. beforehand. However, having them pre-installed can speed up the setup.) R Dependencies: The R scraper uses jsonlite and mongolite packages in R. The script will install them if missing. It will also install the target data science packages in R (like rpart, randomForest, etc.). Make sure your R installation can install packages from CRAN (internet access and write permissions for libraries). Setup Steps:
Clone the Repository: Download or clone the AutoDS project files to your local machine. Navigate to the project directory.
Configure Environment: Create a .env file in the project root (or set environment variables) with your OpenAI API key. For example:
echo 'OPENAI_API_KEY=YOUR_OPENAI_KEY_HERE' > .env
Also ensure that MongoDB is running locally. The default Mongo connection string in the code is mongodb://localhost:27017/. If your setup differs, you’ll need to adjust the Mongo connection string in the code or environment.
Install Python Requirements: Use the provided requirements file or the pip command above to install all Python dependencies. Ensure this is done in a Python environment (virtualenv or Conda env) that you will use to run AutoDS.
Run the Python Function Scraper: This step gathers functions from Python libraries into the MongoDB. Execute:
python python_function_scraper.py
This script will:
Install a predefined list of Python data science packages (if not already installed).
Import each package and extract all functions and their docstrings/signatures.
Insert these function records into the MongoDB AutoDS.python_functions collection.
This process can take some time, as it iterates through many functions. You should see log output indicating how many functions were extracted from each package.
Run the R Function Scraper: To gather R functions, run:
Rscript r_function_scraper.R
This will:
Install the core R packages (from the core_packages list in the script) if not present.
Extract each package’s exported functions, their arguments and help text.
Insert these into the MongoDB AutoDS.r_functions collection.
This also may take a few minutes. Progress and any errors are logged to the console (and to a log file).
Unify the Function Catalog: Now combine the Python and R function data into a single catalog used for querying. Run:
python unify_database.py
This will create/refresh the AutoDS.functions_catalog collection in MongoDB by merging entries from python_functions and r_functions into a consistent format. It will log the count of functions inserted. After this step, the unified catalog holds all functions with keys (descriptions) ready for indexing.
Build the Vector Search Index: Finally, build the FAISS index for semantic search:
python vector_store.py
Running this module will generate embeddings for each function description in the catalog (using the OpenAI API) and store them in a FAISS index file (functions.index along with accompanying files like descriptions.txt and function_map.json). Ensure your OpenAI API key is set before this step. Once completed, you should see logs confirming the index was saved. (If FAISS or OpenAI is not available, this step will log an error or warning. The index is essential for query matching, so this step must succeed for AutoDS to function properly.)
Launch AutoDS CLI: With the database and index ready, you can start the AutoDS interactive agent by running:
python main.py
This will clear the terminal and display the AutoDS welcome header. You can now enter queries at the AutoDS> prompt. Try the help command first to see usage instructions and examples.
If all steps succeeded, AutoDS is now installed and running. In case of issues:
Verify that MongoDB has the AutoDS.functions_catalog collection with documents (you can use MongoDB Compass or the mongo shell to check counts).
Ensure the functions.index file was created in the src/vector directory (or the project directory if paths differ).
Check that your Python environment has rpy2 properly configured (you might need to install R beforehand so that rpy2 can find an R home).
Make sure the OpenAI API key is correct and has access to the embedding API.
Usage Instructions

Using AutoDS is straightforward once the system is running. At the prompt AutoDS>, simply describe the data science task you want to perform in plain English. After pressing Enter, the CLI will ask for function arguments (if any) in JSON format. Basic CLI commands:
Type help to see example queries and instructions on formatting arguments.
Type clear to reset/clear the console screen (on Unix systems).
Type exit to quit the AutoDS CLI.
Query format: You can ask for any analytic or modeling task that might be covered by the libraries in the knowledge base. For example:
"Train a decision tree on my dataset"
"Perform linear regression"
"Cluster my data into 3 groups"
"Calculate the correlation between two variables"
After you enter the query, you’ll see a prompt Args> asking for a JSON object of arguments. If the function you’re requesting needs data or parameters, provide them as JSON key-value pairs. If no arguments are needed or you want to accept all defaults, just press Enter (which submits an empty {} arguments object). Formatting arguments: The JSON should reflect the parameters of the intended function. For instance:
For a clustering task: {"data": [[1,2], [2,3], [3,4], [4,5]], "n_clusters": 2} might be suitable (where “data” is a 2D array of points and “n_clusters” is the number of clusters).
For linear regression in R: {"formula": "y ~ x", "data": "mtcars"} could be used (this uses the built-in R dataset mtcars by name).
For a correlation: {"x": [1,2,3,4], "y": [2,4,6,8]} to compute correlation between two sequences of numbers.
The help command in the CLI will show these examples and more. Ensure your JSON is valid (keys in double quotes, etc.), otherwise AutoDS will notify you of a format error and default to no arguments. What happens next: When you submit the query and arguments, AutoDS will:
Display a processing message (so you know it’s working on it).
Find a function match – using the vector index, it finds the best matching function description. If none is found above a certain threshold, it will return an error that no function was found.
Execute the function – if a match is found, AutoDS calls the function in the appropriate environment. This may take a moment if the function is computationally heavy.
Print the outcome: You will see a success or error message. On success, the CLI shows which language was used (Python or R), followed by the code snippet that was executed, and the result of the function call. On failure, you’ll see an error message, the exception traceback from the function (if available), and some suggestions to troubleshoot (such as checking your arguments).
Example session:
AutoDS> perform linear regression
Enter function arguments as JSON (or press Enter for none):
Args> {"formula": "y ~ x", "data": [[1, 2], [2, 3], [3, 4]]}

Processing your request...

✓ Function executed successfully!

Language: r

Code:
library(stats)
stats::lm(formula="y ~ x", data=rbind(c(1, 2), c(2, 3), c(3, 4)))

Result:
Call:
stats::lm(formula = "y ~ x", data = rbind(c(1, 2), c(2, 3), c(3, 4)))

Coefficients:
(Intercept)            x  
        1.0          0.5  
In the above hypothetical session, AutoDS recognized the query as a linear regression task, chose R’s stats::lm function (since it’s a good match for linear regression by formula), built a code snippet using the provided small dataset, and executed it. The output shows the model call and coefficients. If your query was instead, say, "cluster my data into 3 groups" and you provided a dataset, AutoDS might select sklearn.cluster.KMeans (Python) or stats::kmeans (R) and output the cluster assignments or model summary. Error handling: If something goes wrong (for example, you asked for a random forest but didn’t provide any data), you might see:
✗ Error executing function:
some_function() missing required argument 'data'

Traceback:
... (Python or R error stack trace here) ...

Suggestions:
- Check if the arguments match the function requirements
- Try a more specific query
- Verify the data format is correct
In such cases, you can adjust your input or use the help command to see what arguments might be needed. Finally, when you are done, use exit to quit the program. The log file autods.log will contain a record of your session’s actions, which can be useful for developers or for debugging if needed.
