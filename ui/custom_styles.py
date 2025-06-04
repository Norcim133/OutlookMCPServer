import streamlit as st


def custom_styles():
    st.markdown(
        """
    <style>
        /* Target the main container of a user's chat message */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            flex-direction: row-reverse;
        }

        /* (Optional) Target the content block within a user's chat message to right-align text */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
            text-align: right;
        }

    </style>
    """,
        unsafe_allow_html=True,
    )
