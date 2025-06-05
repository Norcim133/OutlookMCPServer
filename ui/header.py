import streamlit as st


def header():
    col1, col2 = st.columns([5,1])
    with col1:
        st.image("https://i.postimg.cc/vTQrtbS0/horizontal-name-only.jpg", output_format="auto", width=200)

    with col2:
        st.pills("First", options=["Settings", "Reset Chat"], label_visibility="hidden")