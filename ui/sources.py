import logging
import urllib.parse

import streamlit as st

from utils.llama_retrieval import llama_retrieval


def text_sources(nodes_list):
    st.subheader("Text sources")
    try:
        for node in nodes_list:
            if node['type'] == 'text':
                if node['score'] >= .1:
                    with st.container(border=True):
                        expander = st.expander("Text Source")
                        expander.write(node['content'])
                        #st.write(node['metadata'])
                        s3_url = node['url']  # Your full S3 URL
                        encoded_s3_url = urllib.parse.quote_plus(s3_url)
                        google_viewer_url = f"https://docs.google.com/gview?url={encoded_s3_url}&embedded=true"
                        st.link_button("See file", url=google_viewer_url, use_container_width=True, type='tertiary')
                        st.write(f"Relevancy: {node['score']}")
    except Exception as e:
        logging.exception(e)
        st.warning(e)


def img_sources(nodes_list):
    st.subheader("Image sources")
    try:
        for node in nodes_list:
            if node['type'] == 'image':

                if node['score'] >= .1:
                    with st.container(border=True):
                        st.image(node['content'])
                        #st.json(node['metadata'])
                        s3_url = node['url']  # Your full S3 URL
                        encoded_s3_url = urllib.parse.quote_plus(s3_url)
                        google_viewer_url = f"https://docs.google.com/gview?url={encoded_s3_url}&embedded=true"
                        st.link_button(label="See file", url=google_viewer_url, use_container_width=True, type='tertiary')
                        st.write(f"Relevancy: {node['score']}")
    except Exception as e:
        logging.exception(e)
        st.warning(e)


def render_sources(nodes_list, source_type, title, render_content_func):  # Renamed for clarity
    """Generic source renderer that handles common logic."""
    st.subheader(title)
    try:
        for node in nodes_list:
            if node['type'] == source_type and node.get('score', 0) >= 0.1:  # Added .get for score
                with st.container(border=True):
                    # Call the specific rendering function, passing the whole node
                    render_content_func(node)  # Specific renderer now takes the whole node

                    # Common elements
                    source_doc_url = node.get('url')  # Use .get for safety
                    if source_doc_url:
                        encoded_s3_url = urllib.parse.quote_plus(source_doc_url)
                        google_viewer_url = f"https://docs.google.com/gview?url={encoded_s3_url}&embedded=true"
                        # Ensure unique key for link_button
                        node_id = node.get('id', str(id(node)))
                        st.link_button("See file", url=google_viewer_url, use_container_width=True, type='tertiary')
                    st.write(f"Relevancy: {node['score']:.2f}")  # Formatting score
    except Exception as e:
        logging.exception(f"Error rendering {source_type} sources: {e}")  # More specific logging
        st.warning(f"Error displaying {source_type} sources.")


# Content renderers for each type (now take the whole node)
def render_text_content(node):  # Renamed to avoid conflict if you had a previous one

    file_name = "Source"
    if isinstance(node.get('metadata'), dict):
        file_name = node['metadata'].get('file_name', 'Source')

    expander = st.expander(f"Text: {file_name} (Score: {node['score']:.2f})")
    expander.write(node['content'])


def render_image_content(node):  # Renamed
    file_name = "Image"
    if isinstance(node.get('metadata'), dict):
        file_name = node['metadata'].get('file_name', 'Image')

    st.image(node['content'], caption=f"{file_name} (Score: {node['score']:.2f})")


# Your original thin wrappers (optional, could call render_sources directly)
def text_sources_wrapper(nodes_list):  # Renamed
    render_sources(nodes_list, 'text', "Text Sources", render_text_content)


def img_sources_wrapper(nodes_list):  # Renamed
    render_sources(nodes_list, 'image', "Image Sources", render_image_content)


# Main UI function (renamed from sources to avoid conflict with a potential module name)
def source_viewer_display():
    st.header('Source Documents')
    query_nodes_from_state = st.session_state.get('query_nodes', None)

    if not query_nodes_from_state:
        st.info("This will show references for AI responses once a query is made.")
        return

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
    st.info("This will show references for AI responses.")

def sources():
    source_placeholder = st.empty()
    if not st.session_state.get('chat_started', False):
        source_placeholder = source_waiting
        height = 500
    else:
        source_placeholder = source_viewer_display
        height = 1000

    with st.container(border=True, height=height):
        #st.header('Source Documents')
        source_placeholder()


