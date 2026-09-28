import streamlit as st
from pipeline import read_receipt


def main():
    st.title("Receipt Ingredient Extractor")
    uploaded_file = st.file_uploader("Upload a receipt image", type=["jpeg", "png"])
 

if __name__ == "__main__":
    main()