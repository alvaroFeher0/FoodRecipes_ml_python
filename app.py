from datetime import datetime

import streamlit as st
from persistence import list_receipts, load_receipt
from pipeline import pipeline


def show_recipe(recipe):
    cost = recipe.get("cost")
    title = f'{recipe["name"]} · ~€{cost:.2f}' if cost is not None else recipe["name"]
    with st.expander(title):
        st.subheader("Ingredients")
        st.markdown("\n".join(f"- {item}" for item in recipe["ingredients"]))
        st.subheader("Steps")
        st.markdown("\n".join(f"{i}. {step}" for i, step in enumerate(recipe["steps"], 1)))
        if recipe.get("uses"):
            st.subheader("Approximate cost")
            st.markdown("\n".join(
                f'- {u["ingredient"]}: {u["fraction"]:.0%} of the package → €{u["cost"]:.2f}'
                for u in recipe["uses"]
            ))
            st.caption("Estimated from receipt prices and typical package sizes; basic spices not counted.")


def show_saved_recipes():
    st.header("Saved recipes")
    receipts = list_receipts()
    if not receipts:
        st.info("No receipts saved yet. Upload one above to get started.")
        return

    def label(receipt):
        uploaded = datetime.fromisoformat(receipt["uploaded_at"]).astimezone()
        return f'{uploaded:%Y-%m-%d %H:%M} · {receipt["recipe_count"]} recipes'

    receipt = st.selectbox("Receipt", receipts, format_func=label)
    ingredients, recipes = load_receipt(receipt["image_hash"])
    st.write("Ingredients: " + ", ".join(ingredients))
    for recipe in recipes:
        show_recipe(recipe)


def main():
    st.title("Receipt Ingredient Extractor")
    uploaded_file = st.file_uploader("Upload a receipt image", type=["jpeg", "png"])
    
    if uploaded_file:
        with st.spinner("Reading receipt and generating recipes..."):
            ingredients, recipes = pipeline(uploaded_file)
        st.write("Extracted Ingredients:")
        for ingredient in ingredients:
            st.write(f"- {ingredient}")

        st.header("Recipes")
        for recipe in recipes:
            show_recipe(recipe)

    show_saved_recipes()


if __name__ == "__main__":
    main()
