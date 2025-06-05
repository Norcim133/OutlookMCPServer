import logging
import urllib.parse

import streamlit as st

from utils.llama_retrieval import llama_retrieval

def render_sources(nodes_list, source_type, title, render_content_func):
    """Generic source renderer that handles common logic."""
    st.subheader(title)
    try:
        for node in nodes_list:
            if node['type'] == source_type and node.get('score', 0) >= 0.08:
                with st.container(border=True):
                    # Call the specific rendering function, passing the whole node
                    render_content_func(node)  # Specific renderer now takes the whole node

                    # Common elements
                    source_doc_url = node.get('url')  # Use .get for safety
                    if source_doc_url:
                        encoded_s3_url = urllib.parse.quote_plus(source_doc_url)
                        google_viewer_url = f"https://docs.google.com/gview?url={encoded_s3_url}&embedded=true"

                        st.link_button("See file", url=google_viewer_url, type='tertiary', use_container_width=True)
                    st.write(f"Relevancy: {node['score']:.2f}")  # Formatting score
    except Exception as e:
        logging.exception(f"Error rendering {source_type} sources: {e}")  # More specific logging
        st.warning(f"Error displaying {source_type} sources.")


# Content renderers for each type (now take the whole node)
def render_text_content(node):

    file_name = "Source"
    if isinstance(node.get('metadata'), dict):
        file_name = node['metadata'].get('file_name', 'Source')

    expander = st.expander(f"File: {file_name}")
    expander.write(node['content'])


def render_image_content(node):
    file_name = "Image"
    if isinstance(node.get('metadata'), dict):
        file_name = node['metadata'].get('file_name', 'Image')

    st.image(node['content'], caption=f"{file_name}")


def source_viewer_display():

    query_nodes_from_state = st.session_state.get('query_nodes', None)


    try:
        # Assuming llama_retrieval is defined and accessible
        processed_nodes_list = llama_retrieval(query_nodes_from_state)
        if not processed_nodes_list:
            st.info("No source nodes were processed from the query.")
            return

        # Call the generic renderer directly
        render_sources(
            nodes_list=processed_nodes_list,
            source_type='text',
            title="Text Sources",
            render_content_func=render_text_content
        )
        st.divider()
        render_sources(
            nodes_list=processed_nodes_list,
            source_type='image',
            title="Image Sources",
            render_content_func=render_image_content
        )

    except Exception as e:
        logging.exception(f"Error in source_viewer_display: {e}")
        st.error(f"An error occurred while displaying sources: {e}")

def source_waiting():
    st.info("Awaiting AI response to begin...")


def sources():
    container_height = 1000 if st.session_state.get('chat_started', False) else 500  # Adjusted for waiting message
    with st.container(border=True, height=container_height):  # Determine height based on state first


        st.header('Source Documents')
        if not st.session_state.get('chat_started', False):
            source_waiting()
        else:
            source_viewer_display()


