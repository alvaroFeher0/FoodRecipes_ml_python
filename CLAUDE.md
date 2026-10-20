# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

**foodML** — a Streamlit app that takes a photo of a (Spanish) supermarket receipt, uses a vision LLM to map each product line to a generic English ingredient with its price, then asks an LLM for recipes built from those ingredients and estimates each recipe's cost. Results are cached in a local SQLite DB keyed by the image's hash.

Personal learning project: favour clear, readable code over abstraction, and explain non-obvious ML/LLM choices in comments or the PR description.

## Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .             # installs src/foodml as an importable package
cp env_example .env          # then set GROQ_API_KEY
streamlit run src/foodml/app/app.py   # main entry point
```

There is no test suite or linter configured yet. `data/raw/receipt1.jpeg` is the sample receipt for manual testing.

## Layout

cookiecutter-data-science style. Code lives in the `src/foodml/` package and uses absolute imports (`from foodml.models.llm import call_model`). Top-level `data/` (raw/interim/processed), `notebooks/`, `configs/`, `models/` (trained weights, not code), `reports/` and `tests/` are placeholders for the ML roadmap below. `features/` and `evaluation/` in the package are empty for now. `.env` and `foodml.db` stay at the repo root: `llm.py` and `persistence.py` resolve them relative to their own location.

## Architecture

Data flows strictly left to right (paths relative to `src/foodml/`):

```
app/app.py (UI) → pipelines/receipt_pipeline.py → models/receipt_reader.py → models/llm.py
                                                → models/recipe_generator.py → models/llm.py
                                                → data/persistence.py (SQLite: foodml.db)
```

| File | Role |
|---|---|
| `app/app.py` | Streamlit UI: upload, show extracted ingredients + recipes, browse saved receipts. No business logic. |
| `pipelines/receipt_pipeline.py` | Orchestrator. Hash image → return cached result if seen → extract → normalise (lowercase, numeric prices, sum duplicate ingredients) → generate recipes → save. Returns `(ingredients, recipes)`. |
| `models/receipt_reader.py` | Resizes/rotates the photo (EXIF, max 2000px, JPEG q85) and sends it as a base64 data URL with the extraction prompt. Returns a DataFrame. |
| `models/recipe_generator.py` | Prompts for `n` recipes with per-ingredient package `fraction`s, then `add_cost()` computes cost locally (price × fraction, capped at 1 package). |
| `models/llm.py` | Single `call_model(content)` helper: Groq via the OpenAI SDK (`base_url=https://api.groq.com/openai/v1`), JSON mode, `temperature=0`, strips `<think>` blocks, slices to the outermost `{...}`. |
| `data/persistence.py` | SQLite schema (`receipts`, `items`, `recipes`), `connect()` context manager with lightweight in-place migrations, `hash_image`, `save_receipt`, `load_receipt`, `list_receipts`. |

### Data contracts

- Extraction JSON: `{"items": [{"line", "ingredient" | null, "price" | null}]}` — `null` ingredient = non-food line.
- Recipe JSON: `{"recipes": [{"name", "ingredients": [str], "steps": [str], "uses": [{"ingredient", "fraction"}]}]}`. After `add_cost`, each recipe also has `uses[].cost` and `cost` (float or `None`).
- `uses[].ingredient` must match the keys of the `prices` dict exactly (lowercased); unmatched names are silently dropped from the cost.

## Conventions

- All LLM calls go through `foodml.models.llm.call_model`. Don't instantiate new clients elsewhere; switching provider/model should only touch `models/llm.py` and `.env` (`GROQ_API_KEY`, optional `GROQ_MODEL`).
- Prompts ask for JSON and say the exact schema inline. When changing a prompt, update the consumer code and the contracts above together.
- Do arithmetic (costs, sums) in Python, not in the LLM.
- Schema changes: add them in `connect()` as idempotent checks (see the `approx_cost` migration) — existing `foodml.db` files must keep working.
- `hash_image` must leave uploaded files seekable (`file.seek(0)`); preserve that if you touch it.
- Never commit `.env` or `foodml.db`.

## Known issues (as of the latest commit)

1. **Price column is dropped.** `models/receipt_reader.extract_ingredients` builds the DataFrame with `columns=["line", "ingredient"]`, so `price` is discarded and `receipt_pipeline.py` raises `KeyError: 'price'` for any new receipt. Fix: add `"price"` to `columns`.
2. Prices and `uses` aren't persisted, so reloaded receipts show the total cost but no per-ingredient breakdown. Fix needs new columns (`items.price`, a JSON `recipes.uses`) via the migration pattern above.
3. `models/receipt_reader.py` has unused imports (`json`, `os`, `re`, `dotenv`, `OpenAI`).
4. `__pycache__/` and `.DS_Store` files are committed despite `.gitignore`; remove them with `git rm --cached`.
5. Debug `print`s in `pipelines/receipt_pipeline.py` — fine for now, move to `logging` if they get noisy.

## Roadmap / ideas under consideration

Context for design decisions — don't build these unprompted:

- Upload a **fridge photo** to detect available food (likely a second extraction path feeding the same `prices`/ingredients structure).
- A **recommendation system** over recipes / user history.
- **Agentic patterns**: reflection (critique and revise recipes), tool use, planning, multi-agent.
- **Fine-tuning** a model on free cookbooks and recipe datasets to generate recipes from inventory — a full pipeline (data prep → training → eval), possibly BERT-based where it fits (e.g. ingredient normalisation/classification).
- Earlier versions used local Ollama + EasyOCR; the current vision-LLM approach replaced that.

When implementing any of these, keep `pipelines/receipt_pipeline.py` as the single orchestrator (new flows go in `pipelines/`) and add new stages as separate modules in the matching package folder.