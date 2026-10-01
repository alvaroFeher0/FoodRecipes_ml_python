import os
from dotenv import load_dotenv
from openai import OpenAI
from receipt_reader import extract_ingredients
from recepies_generator import generate_recipes

def pipeline(file):
    mapping = extract_ingredients(file)  # "receipts/receipt1.jpeg"
    ingredients = sorted(mapping["ingredient"].dropna().str.lower().unique())
    print(ingredients)

    recipes = generate_recipes(ingredients)
    for recipe in recipes:
        print(f"\n## {recipe['name']}")
        for item in recipe["ingredients"]:
            print(f"- {item}")
        for i, step in enumerate(recipe["steps"], 1):
            print(f"{i}. {step}")
    return ingredients, recipes
