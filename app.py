#Chat related

from mcpserver.pipeline import RAGService
import logging
from errors import *
from ui.chatbot import chatbot
from ui.custom_styles import *
from ui.sources import sources
from ui.indices import indices
from ui.header import header


def st_side_bar():
    with st.sidebar:
        st.title("Query Sources")

        #dashboard()

        indices()


def app_body():

    st.logo(
        "assets/horizontal_NB.png",
        size="large",
        icon_image="assets/square_NB.png"
    )

    st_side_bar()

    c1, c2 = st.columns([2,1], vertical_alignment="top", gap="large")
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
    st.set_page_config(page_title="Proof", page_icon=":apple:", layout="wide", menu_items=None)

    header()
    #HTML for control over streamlit components
    alternate_chat_side_style()
    container_shadow_styles()


    try:

        if st.session_state.refresh_state:
            init_RAGService()

        app_body()

    except CriticalInitializationError as e:
        st.warning(f"The controller could not be initialized\n\n Error code: {e} \n\nPlease try again later.")




main()