# AutoDS - Automated Data Science Assistant

AutoDS is an AI-powered CLI tool that interprets natural language queries (e.g. “Train a decision tree”) and automatically calls relevant data science functions from Python or R.

---

## Key Features
- **Semantic Search**: Uses OpenAI embeddings + FAISS to match queries to function descriptions.
- **Multi-Language**: Executes Python or R functions (via rpy2).
- **Automatic Execution**: Dynamically imports and runs matched functions.
- **CLI Interface**: Type queries, provide JSON arguments, and see results (or errors) in the terminal.

---

## Limitations
- User must build the function database (via scrapers) before use.
- CLI cannot show plots/GUI output; only textual results.

---

## Installation

1. **Install Dependencies**  
   - Python 3.x, R (4.x recommended), MongoDB (running on `localhost:27017`), and an OpenAI API key.
   - Python packages (example):
     ```bash
     pip install pymongo faiss-cpu openai python-dotenv colorama rpy2 numpy
     ```
2. **Clone & Configure**  
   ```bash
   git clone https://github.com/YourUsername/AutoDS.git
   cd AutoDS
   echo 'OPENAI_API_KEY=YOUR_KEY' > .env
3. **Populate Database**
   - Run Python scraper:
   - python python_function_scraper.py
   - Run R scraper:
   - Rscript r_function_scraper.R
   - Unify:
   - python unify_database.py
   - Build FAISS index:
   - python vector_store.py
     
## Usage

1. Start the CLI
   - python main.py
2. Enter a Query (e.g. “Perform linear regression”).
3. Provide JSON Args (or leave empty for defaults):
   - {"formula": "y ~ x", "data": "mtcars"}
4. View Results
   - AutoDS shows the chosen function, the code snippet, and its output or any error messages.
5. CLI Commands
   - help for examples
   - clear to clear screen
   - exit to quit

## Example 

AutoDS> perform linear regression
Args> {"formula": "y ~ x", "data": [[1,2], [2,3], [3,4]]}

✓ Success!
Language: r
Code:
library(stats)
stats::lm(formula="y ~ x", data=rbind(c(1, 2), c(2, 3), c(3, 4)))

Result:
Coefficients:
(Intercept)   x
        1.0  0.5


