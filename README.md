# AutoDS - AI Agent for Python/R

AutoDS automates data science tasks by processing queries (e.g., "linear regression") to execute Python/R functions using MongoDB, FAISS, and OpenAI embeddings.

## Features
- Natural language queries for Python/R functions.
- Fast function retrieval with FAISS and OpenAI.
- Cross-language support (Python, R).

## Installation
- **Needs:** Python 3.9+, R, MongoDB, OpenAI API key.
- **Steps:**
  1. Clone: `git clone <repo>; cd AutoDS`
  2. Virtual env: `python -m venv venv; source venv/bin/activate` (Windows: `venv\Scripts\activate`)
  3. Install: `pip install -r requirements.txt` (add `scikit-learn`)
  4. Set `.env` with `MONGO_URI` and `OPENAI_API_KEY`
  5. Seed DB: `python src/db/seed_db.py`
  6. Build FAISS: `python src/vector/vector_store.py`


Summary of Remaining Work

Here’s a concise list of tasks, prioritized by effort and impact:

Expand Database:
Automate scraping for 100+ packages, populate functions.json or MongoDB, test scalability.
Enhance Python Execution:
Update python_exec.py for class-based functions, test with DecisionTreeClassifier.
Automate Argument Handling:
Add inference/validation in agent.py or main.py, improve user prompts.
Implement OpenAI Search:
Optional, replace or supplement FAISS with OpenAI file search, evaluate performance.
Add Code/Language Output:
Modify agent.py to return generated code and language, test with queries.
Update README:
Expand README.md to match AutoDS.md requirements, include detailed examples.

## Usage
```bash PYTHONPATH="${PYTHONPATH}:/Users/varshithgowdak/Desktop/AutoDS" python src/main.py
## Try: linear regression with {"formula": "y ~ x", "data": [[1, 2], [2, 3], [3, 4]]}.
