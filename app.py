import streamlit as st
from llama_cloud.client import LlamaCloud
from llama_cloud.core import ApiError

from mcpserver.pipeline import SyncPipelineController
import os
import logging
from errors import *
import time

def org_info():
    st.subheader("Org ID")
    st.write(st.session_state.llama.organization_id)

def project_info():
    st.subheader("Project ID")
    st.write(st.session_state.llama.project_id)

def indices_list_view():
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

def set_index_state_with_selector():
    st.session_state.current_index_name = st.session_state.get('indices_selector', None)


def indices_selector():
    st.subheader("Theme Selector")
    st.selectbox("Select a Theme",
                 options = st.session_state.llama.indices,
                 key = "indices_selector",
                 on_change=set_index_state_with_selector,
                 index = next((i for i, k in enumerate(st.session_state.llama.indices) if k == st.session_state.get('current_index_name')), None))
                 # Get index but reverts to first item in keys if item not there
    st.subheader("Current Theme")
    st.write(st.session_state.get('current_index_name', None))

def rename_index():
    current_index_name = st.session_state.get('current_index_name', None)
    try:
        st.session_state['current_index_name'] = st.session_state.llama.rename_pipeline(new_name=st.session_state.get("rename_dialog_new_name_input", None),
                                               pipeline_id=st.session_state.llama.indices.get(current_index_name, None))

        st.session_state.refresh_state = True
        return True
    except Exception as e:
        st.error(f"Error renaming index: ", e)
        return False

def rename_index_component():

    @st.dialog("Rename Theme")
    def index_rename_dialog():
        st.session_state['show_rename_index_dialog'] = False
        current_index_name = st.session_state.get('current_index_name', None)
        if current_index_name is None:
            st.warning("No current index name selected.")
        else:
            st.write(f"Changing name for theme: {current_index_name}")
            new_name_input = st.text_input("New name:",
                                           key="rename_dialog_new_name_input",
                                           placeholder="Enter new name")

            if st.button("Save Rename",
                         key="rename_dialog_save_btn"
                         ):
                if rename_index():
                    st.success(f"Successfully sent request to rename '{current_index_name}' to '{st.session_state['current_index_name']}'.")
                else:
                    st.success(
                        f"Failed to rename '{current_index_name}'.")
                time.sleep(2)
                st.rerun()

    st.button("Rename Theme",
              on_click=index_rename_dialog,
              disabled=not st.session_state.get('indices_selector', False)
              )

    if st.session_state.get("show_rename_index_dialog", False):
        index_rename_dialog()

def indices():
    try:
        if "current_index_name" not in st.session_state:
            st.session_state['current_index_name'] = None

        indices_list_view()

        indices_selector()

        rename_index_component()
    except Exception as e:
        st.error(e)

def st_side_bar():
    with st.sidebar:
        org_info()

        project_info()

        indices()


def llama_chatbot(query):
    from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
    from llama_index.core.memory import ChatMemoryBuffer
    from llama_index.core.chat_engine import CondensePlusContextChatEngine
    from llama_index.llms.openai import OpenAI

    llm = OpenAI(model="gpt-3.5-turbo")

    memory = ChatMemoryBuffer.from_defaults(token_limit=3900)

    pipeline_id = st.session_state.llama.indices[st.session_state.current_index_name]
    st.write(pipeline_id)
    api_key = st.secrets["LLAMA_CLOUD_API_KEY"]
    index = LlamaCloudIndex(
        id=pipeline_id,
        project_id=st.session_state.llama.project_id,
        api_key=api_key
    )

    st.session_state['chat_engine'] = CondensePlusContextChatEngine.from_defaults(
        index.as_retriever(),
        chat_mode="condense_plus_context",
        memory=memory,
        llm=llm,
        context_prompt=(
            "You are a chatbot, able to have normal interactions, as well as talk"
            " about speed and value in large enterprises."
            "Here are the relevant documents for the context:\n"
            "{context_str}"
            "\nInstruction: Use the previous chat history, or the context above, to interact and help the user."
        ),
        verbose=False,
    )

    with st.chat_message("assistant"):

        response = st.write_stream(st.session_state.chat_engine.stream_chat(query).response_gen)
    st.session_state.messages.append({"role": "assistant", "content": response})

def chatbot():
    st.title("Chat Bot")


    try:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # React to user input
        if prompt := st.chat_input("What is up?"):
            # Display user message in chat message container
            st.chat_message("user").markdown(prompt)
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

            llama_chatbot(prompt)



    except Exception as e:
        st.error(e)
        logging.exception(e)
        st.warning("An error occurred with chat input.")

    if st.button("Reset chat state"):
        st.session_state.chat_engine.reset()

def app_body():

    st_side_bar()

    chatbot()


# st.cache_resource
def init_controller():
    # Streamlit doesn't support .env
    try:
        controller = SyncPipelineController()
        st.session_state["llama"] = controller
    except Exception as e:
        logging.error(f"Failed to initialize controller: {str(e)}")
        raise CriticalInitializationError(f"Failed to initialize controller: {str(e)}")
    st.session_state.refresh_state = False

def main():
    if 'refresh_state' not in st.session_state:
        st.session_state['refresh_state'] = True

    st.set_page_config(page_title="Board Seeker", page_icon=":apple:", )
    try:
        if st.session_state.refresh_state:
            init_controller()

        app_body()
    except CriticalInitializationError as e:
        st.warning(f"The controller could not be initialized\n\n Error code: {e} \n\nPlease try again later.")



main()