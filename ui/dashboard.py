import streamlit as st


def org_info():
    st.subheader("Org ID")
    st.write(st.session_state.llama.organization_id)


def project_info():
    st.subheader("Project ID")
    st.write(st.session_state.llama.project_id)


def dashboard():
    org_info()

    project_info()
