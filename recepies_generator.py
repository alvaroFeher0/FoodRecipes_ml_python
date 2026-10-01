from llm import call_model

def generate_recipes(ingredients, n=3):
    """Ask the model for n recipes that mainly use the given ingredients."""
    prompt = (
        f"Suggest {n} recipes that mainly use these ingredients "
        "(you may assume salt, pepper, water and basic spices). "
        "Each recipe should use only the ingredients that make sense together; "
        "skip any that don't fit (e.g. sweets in a savory dish): " + ", ".join(ingredients) + "\n\n"
        'Reply with JSON: {"recipes": [{"name": "...", "ingredients": ["..."], "steps": ["..."]}]}'
    )
    return call_model(prompt)["recipes"]