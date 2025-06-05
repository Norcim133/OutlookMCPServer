import logging

import streamlit as st
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.llms.openai import OpenAI
from utils.llama_retrieval import *


from .indices import *

#TODO: Include history as context
#TODO: Save history
#TODO: Limit history

logger = logging.getLogger(__name__)

@st.cache_resource
def llama_chatbot(current_index_name):

    llm = OpenAI(model="gpt-3.5-turbo")

    memory = ChatMemoryBuffer.from_defaults(token_limit=3900)

    pipeline_id = st.session_state.llama.indices[current_index_name]

    api_key = st.secrets["LLAMA_CLOUD_API_KEY"]
    index = LlamaCloudIndex(
        id=pipeline_id,
        project_id=st.session_state.llama.project_id,
        api_key=api_key
    )

    chat_engine = CondensePlusContextChatEngine.from_defaults(
        index.as_retriever(),
        chat_mode="condense_plus_context",
        memory=memory,
        llm=llm,
        context_prompt=(
            "You are a chatbot, the plays expert on the documents stored by the company."
            "Your only focus is on understanding those documents at a factual level."
            "The content for those documents is here:\n"
            "{context_str}"
            "\nInstruction: Use the previous chat history, or the context above, to interact and answer user questions about the documents."
            "IMPORTANT: You do not bring other knowledge to responses beyond the document and chat context."
            "If there are questions that can't be answered by the documents or chat, then simply say that is outside the scope of your memory."
        ),
        verbose=False,
    )

    return chat_engine

@st.fragment
def chatbot():
    if st.session_state.get('current_index_name', None) is None:
        st.warning("Select an index to get started")
        return

    if 'chat_engine' not in st.session_state:
        try:
            st.session_state.chat_engine = llama_chatbot(st.session_state.get('current_index_name', None))
        except Exception as e:
            logging.exception(f"CHATBOT: {e}")
            raise e
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "chat_started" not in st.session_state:
        st.session_state.chat_started = False

    try:
        with st.container(height=500):

            if not st.session_state.chat_started:
                st.info("Ask a question about your files")
                logger.info("Chat not started")

            else:
                logger.info("Chat has started")
                # Display chat messages from history on app rerun
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

            user_placeholder = st.empty()

            ai_placeholder = st.empty()

            # React to user input
        if prompt := st.chat_input("Ask a question", disabled=not st.session_state.get('current_index_name', None)):
            # Display user message in chat message container
            st.session_state.chat_started = True
            with user_placeholder:
                st.chat_message("user").markdown(prompt)
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

            st.session_state.query_nodes = st.session_state.llama.multi_modal_retrieval(query_text=prompt, pipeline_name=st.session_state.get('current_index_name', None))

            with ai_placeholder:
                with st.chat_message("assistant"):

                    response = st.write_stream(st.session_state.chat_engine.stream_chat(prompt).response_gen)
                    #response = "Hi there testing"
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

    except Exception as e:
        st.error(e)
        logging.exception(e)
        st.warning(f"An error occurred with chat input. Please try again later.")


