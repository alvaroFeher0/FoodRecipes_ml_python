from llm import call_model

def generate_recipes(prices, n=3):
    """Ask the model for n recipes that mainly use the bought ingredients and estimate each one's cost.

    prices maps each ingredient to what was paid for it (None if unknown).
    """
    listing = "\n".join(
        f"- {name}: {'€%.2f' % price if price is not None else 'price unknown'}" for name, price in prices.items()
    )
    prompt = (
        f"Suggest {n} recipes that mainly use these ingredients bought at the supermarket "
        "(you may assume salt, pepper, water and basic spices). "
        "Each recipe should use only the ingredients that make sense together; "
        "skip any that don't fit (e.g. sweets in a savory dish).\n\n"
        f"Ingredients with the price paid for the whole package:\n{listing}\n\n"
        "For each recipe, list in \"uses\" every bought ingredient it needs, with the name exactly as "
        "written above and the fraction of the package one recipe consumes (0 to 1), assuming typical "
        "supermarket package sizes (e.g. 2 tablespoons of a 1 L bottle of olive oil -> 0.03).\n\n"
        'Reply with JSON: {"recipes": [{"name": "...", "ingredients": ["..."], "steps": ["..."], '
        '"uses": [{"ingredient": "...", "fraction": 0.25}]}]}'
    )
    recipes = call_model(prompt)["recipes"]
    for recipe in recipes:
        add_cost(recipe, prices)
    return recipes


def add_cost(recipe, prices):
    """Set recipe["cost"] to the sum of price x fraction for the bought ingredients it uses."""
    fractions = {}
    for use in recipe.get("uses", []):
        name = str(use.get("ingredient", "")).lower()
        if prices.get(name) is None:  # not on the receipt or price unreadable
            continue
        # merge repeated entries and never use more than the whole package
        fractions[name] = min(fractions.get(name, 0) + max(float(use.get("fraction") or 0), 0), 1)
    uses = [{"ingredient": name, "fraction": f, "cost": round(prices[name] * f, 2)} for name, f in fractions.items()]
    recipe["uses"] = uses
    recipe["cost"] = round(sum(u["cost"] for u in uses), 2) if uses else None
