import streamlit as st
from pipeline import pipeline


def main():
    st.title("Receipt Ingredient Extractor")
    uploaded_file = st.file_uploader("Upload a receipt image", type=["jpeg", "png"])
    
    if uploaded_file:
        ingredients = pipeline(uploaded_file)
        st.write("Extracted Ingredients:")
        for ingredient in ingredients:
            st.write(f"- {ingredient}")

if __name__ == "__main__":
    main()