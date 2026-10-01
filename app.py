import streamlit as st
from pipeline import pipeline


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
            with st.expander(recipe["name"]):
                st.subheader("Ingredients")
                st.markdown("\n".join(f"- {item}" for item in recipe["ingredients"]))
                st.subheader("Steps")
                st.markdown("\n".join(f"{i}. {step}" for i, step in enumerate(recipe["steps"], 1)))

if __name__ == "__main__":
    main()
