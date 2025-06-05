import streamlit as st
import logging

logger = logging.getLogger(__name__)

def header():
    col1, col2 = st.columns([5,1])
    with col1:
        st.image("https://i.postimg.cc/vTQrtbS0/horizontal-name-only.jpg", output_format="auto", width=200)

    with col2:
        st.session_state.settings_pills = None
        selection = st.pills("First",
                             options=["Settings", "Reset Chat"],
                             label_visibility="hidden",
                             selection_mode="single",
                             default=None,
                             key="settings_pills"
                             )
        logger.info(f"selection: {selection}")
        if selection == "Reset Chat":
            logger.info("Resetting chat settings")
            if st.session_state.chat_engine:
                st.session_state.chat_engine.reset()
            st.session_state.chat_started = False
            st.session_state.messages = []

            logger.error("Resetting chat")
            #st.rerun()
