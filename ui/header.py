import streamlit as st
import logging

logger = logging.getLogger(__name__)

def handle_settings_pills():
    try:
        selection = st.session_state.get('settings_pills', None)

        if selection == "Reset Chat":
            logger.info("Resetting chat settings")
            if st.session_state.chat_engine:
                st.session_state.chat_engine.reset()
            st.session_state.chat_started = False
            st.session_state.messages = []

            logger.info("Resetting chat")

        elif selection == "Settings":
            pass
        else:
            pass
    except Exception as e:
        st.warning("Issue resetting chat settings")
        logger.exception(e)

def header():
    col1, col2 = st.columns([5,1])
    with col1:
        st.image("https://i.postimg.cc/vTQrtbS0/horizontal-name-only.jpg", output_format="auto", width=200)

    with col2:
        st.session_state.settings_pills = None
        st.pills("First",
                 options=["Settings", "Reset Chat"],
                 label_visibility="hidden",
                 selection_mode="single",
                 default=None,
                 key="settings_pills",
                 on_change=handle_settings_pills
                 )

