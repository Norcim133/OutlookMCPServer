import streamlit as st

#Chat related

from mcpserver.pipeline import RAGService
import logging
from errors import *
from ui.chatbot import chatbot
from ui.custom_styles import custom_styles
from ui.dashboard import dashboard
from ui.file_manager import file_manager
from utils.llama_retrieval import llama_retrieval

from ui.indices import indices
import json


def text_sources(nodes_list):
    try:
        for node in nodes_list:
            if node['type'] == 'text':
                if node['score'] >= .1:
                    with st.container(border=True):
                        expander = st.expander("Text Source")
                        expander.write(node['content'])
                        st.write(node['metadata'])
                        st.write(f"Relevancy: {node['score']}")
                        st.write(f"Url: {node['url']}")
    except Exception as e:
        st.warning(e)

def img_sources(nodes_list):
    try:
        for node in nodes_list:
            if node['type'] == 'image':

                if node['score'] >= .1:
                    with st.container(border=True):
                        st.image(node['content'])
                        st.json(node['metadata'])
                        st.write(f"Relevancy: {node['score']}")
                        st.write(f"Url: {node['url']}")
    except Exception as e:
        st.warning(e)

def sources():
    st.header('Source Documents')
    if not st.session_state.get('query_nodes', None):
        st.info("This will show references for AI responses.")
        return
    nodes_list = llama_retrieval(st.session_state.get('query_nodes', None))

    try:
        text_sources(nodes_list)

        img_sources(nodes_list)

    except Exception as e:
        logging.exception(e)
        st.error(e)

def st_side_bar():
    with st.sidebar:
        st.title("Board Diver")

        #dashboard()

        indices()


def app_body():

    st_side_bar()

    c1, c2 = st.columns([2,1], border=True, vertical_alignment="top")
    with c1:
        chatbot()

    with c2:
        #file_manager()
        sources()

# st.cache_resource
def init_RAGService():
    # Streamlit doesn't support .env
    try:
        rag_service = RAGService()
        st.session_state["llama"] = rag_service
    except Exception as e:
        logging.error(f"Failed to initialize rag_service: {str(e)}")
        raise CriticalInitializationError(f"Failed to initialize rag_service: {str(e)}")
    st.session_state.refresh_state = False

def main():
    #Refresh state used for changes to llamacloud objects org, project, indices
    #Set to true for first run of app
    if 'refresh_state' not in st.session_state:
        st.session_state['refresh_state'] = True

    #Boilerplate config for all streamlit apps
    st.set_page_config(page_title="Board Seeker", page_icon=":apple:", layout="wide")

    #HTML for control over streamlit components
    custom_styles()


    try:

        if st.session_state.refresh_state:
            init_RAGService()

        app_body()

    except CriticalInitializationError as e:
        st.warning(f"The controller could not be initialized\n\n Error code: {e} \n\nPlease try again later.")




main()