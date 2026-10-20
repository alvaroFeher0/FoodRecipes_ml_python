import pandas as pd
from persistence import hash_image, load_receipt, save_receipt
from receipt_reader import extract_ingredients
from recepies_generator import generate_recipes

def pipeline(file):
    image_hash = hash_image(file)
    saved = load_receipt(image_hash)
    if saved:
        print("Receipt already processed, loaded from the database")
        return saved

    mapping = extract_ingredients(file)  # "receipts/receipt1.jpeg"
    mapping["ingredient"] = mapping["ingredient"].str.lower()
    mapping["price"] = pd.to_numeric(mapping["price"], errors="coerce")
    # same ingredient on several lines (e.g. two kinds of tomatoes) -> add their prices up
    prices = mapping.dropna(subset=["ingredient"]).groupby("ingredient")["price"].sum(min_count=1)
    prices = {name: (None if pd.isna(price) else float(price)) for name, price in prices.items()}
    ingredients = sorted(prices)
    print(prices)

    recipes = generate_recipes(prices)
    for recipe in recipes:
        print(f"\n## {recipe['name']}")
        for item in recipe["ingredients"]:
            print(f"- {item}")
        for i, step in enumerate(recipe["steps"], 1):
            print(f"{i}. {step}")
        print(f"Approx. cost: {recipe['cost']}")

    save_receipt(image_hash, mapping, recipes)
    return ingredients, recipes
