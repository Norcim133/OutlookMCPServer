import streamlit as st
from llama_cloud.client import LlamaCloud
from mcpserver.pipeline import SyncPipelineController
import os
import logging
from errors import *

def org_info():
    st.subheader("Org ID")
    st.write(st.session_state.llama.organization_id)

def project_info():
    st.subheader("Project ID")
    st.write(st.session_state.llama.project_id)

def indices_list():
    st.subheader("Index IDs")
    try:
        indices_data = st.session_state.llama.indices

        if not indices_data: # This now cleanly handles the {} case for "no indices"
            st.info("No indices found for the default project.")
        else:
            for key, value in indices_data.items():
                st.write(f"**{key}**: {value}")

    except LlamaOperationFailedError as e: # Catch operational errors from the API call
        st.warning(f"API call to fetch llama indices failed: {e}")
        logging.error(f"API call to fetch llama indices failed: {e}")
    except Exception as e: # Catch any other truly unexpected error
        st.error("An unexpected error occurred while displaying indices.")
        logging.exception("Error in indices_display component")

def set_index():
    st.session_state.index = st.session_state.get('indices_selector', None)

def indices_selector():
    st.subheader("Index Selector")
    selection = st.selectbox("Select a Theme",
                 options = st.session_state.llama.indices,
                 key = "indices_selector",
                 on_change=set_index)

    if st.session_state.get('indices_selector', None) is not None:
        st.write(st.session_state['indices_selector'])
    else:
        st.write("Fail pig")

def st_side_bar():
    with st.sidebar:
        org_info()

        project_info()

        indices_list()

        indices_selector()



def app_body():

    st_side_bar()

    st.title("Chat Bot")



@st.cache_resource
def init_controller():
    # Streamlit doesn't support .env
    try:
        controller = SyncPipelineController()
        st.session_state["llama"] = controller
        st.session_state.app_init = True
    except Exception as e:
        logging.error(f"Failed to initialize controller: {str(e)}")
        raise CriticalInitializationError(f"Failed to initialize controller: {str(e)}")

def main():

    st.set_page_config(page_title="Board Seeker", page_icon=":apple:", )
    try:
        init_controller()
        app_body()
    except CriticalInitializationError as e:
        st.warning(f"The controller could not be initialized\n\n Error code: {e} \n\nPlease try again later.")



main()