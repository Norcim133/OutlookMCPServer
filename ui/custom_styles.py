import streamlit as st


def alternate_chat_side_style():
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

def container_shadow_styles():
    shadow_css = """
    <style>
    /* Apply shadow to stVerticalBlockBorderWrapper when it's a direct child of stVerticalBlock,
       BUT NOT if it's part of a dialog,
       AND NOT if it contains an stChatInput element anywhere inside it. */
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"]:not([aria-label="dialog"] *):not(:has([data-testid="stChatInput"])) {
        box-shadow: 5px 5px 5px rgba(0, 0, 0, 0.2);
        border-radius: 0.5rem;
        transition: box-shadow 0.3s ease;
    }
    </style>
    """
    st.markdown(shadow_css, unsafe_allow_html=True)