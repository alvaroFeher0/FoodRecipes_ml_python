# foodML

Take a photo of a supermarket receipt and get recipes you can cook with what you bought, plus an estimate of what each recipe costs.

foodML is a Streamlit app. A vision LLM (via [Groq](https://groq.com)) reads the receipt and turns each product line into a generic ingredient with its price. A second LLM call suggests recipes that use those ingredients, and the app works out each recipe's cost from the prices on the receipt. Results are cached in a local SQLite database, so uploading the same photo again won't call the API.

## Requirements

- Python 3.10+
- A Groq API key (free at [console.groq.com](https://console.groq.com/keys))

## Setup

```bash
git clone <this-repo-url>
cd FoodML_project_python

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .                 # makes the src/foodml package importable

cp env_example .env
```

Open `.env` and set your key:

```
GROQ_API_KEY=your_groq_api_key
# optional, defaults to qwen/qwen3.8-27b
# GROQ_MODEL=qwen/qwen3.8-27b
```

## Run

```bash
streamlit run src/foodml/app/app.py
```

Streamlit opens the app at <http://localhost:8501>. Upload a receipt photo to try it; there's a sample at `data/raw/receipt1.jpeg`. Earlier receipts can be reopened from the app.

## Project structure

The layout follows the [cookiecutter-data-science](https://cookiecutter-data-science.drivendata.org/) convention: the code is an installable package in `src/foodml/`, and the Streamlit app is just one consumer of it.

```
├── data/
│   ├── raw/              # input data: receipt photos (sample: receipt1.jpeg)
│   ├── interim/          # intermediate outputs (not in git)
│   └── processed/        # final datasets for training/evaluation (not in git)
├── notebooks/            # exploration and experiments
├── configs/              # model and experiment settings
├── models/               # trained model weights / checkpoints (not in git)
├── reports/              # evaluation results and figures
├── src/foodml/
│   ├── app/              # Streamlit UI
│   ├── pipelines/        # end-to-end flows that chain the steps together
│   ├── models/           # LLM client and model calls (extraction, recipe generation)
│   ├── data/             # storage (SQLite)
│   ├── features/         # ingredient normalisation / feature engineering
│   └── evaluation/       # metrics for extraction and recipes
├── tests/
└── pyproject.toml
```

## How it works

```
app/app.py (UI) → pipelines/receipt_pipeline.py → models/receipt_reader.py   → models/llm.py   (photo → ingredients + prices)
                                                → models/recipe_generator.py → models/llm.py   (ingredients → recipes + cost)
                                                → data/persistence.py                         (SQLite cache: foodml.db)
```

| File (in `src/foodml/`) | What it does |
|---|---|
| `app/app.py` | Streamlit interface |
| `pipelines/receipt_pipeline.py` | Runs the steps in order and checks the cache first |
| `models/receipt_reader.py` | Prepares the photo and pulls the ingredients and prices out of it |
| `models/recipe_generator.py` | Asks for recipes and calculates their cost |
| `models/llm.py` | The one place that calls the Groq API |
| `data/persistence.py` | SQLite storage, keyed by a hash of the image |

## Notes

- The prompts expect Spanish supermarket receipts.
- `foodml.db` is created at the repo root on first run. To clear the cache, delete it.
- Keep `.env` and `foodml.db` out of git.
