import logging
import time

import streamlit as st

from errors import LlamaOperationFailedError


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
    #st.subheader("Theme Selector")

    st.selectbox("Select a Theme",
                 options = st.session_state.llama.indices,
                 key = "indices_selector",
                 on_change=set_index_state_with_selector,
                 index = next((i for i, k in enumerate(st.session_state.llama.indices) if k == st.session_state.get('current_index_name')), None))
                 # Get index but reverts to first item in keys if item not there

    st.subheader("Current Theme")
    for theme in st.session_state.llama.indices.keys():
        st.button(theme, use_container_width=True)
    #st.write(st.session_state.get('current_index_name', None))


def rename_index():
    current_index_name = st.session_state.get('current_index_name', None)
    try:
        st.session_state['current_index_name'] = st.session_state.llama.rename_pipeline(new_name=st.session_state.get("rename_dialog_new_name_input", None),
                                               pipeline_id=st.session_state.llama.indices.get(current_index_name, None))

        st.session_state.refresh_state = True
        return True
    except Exception as e:
        st.error(f"Error renaming index: {e}")
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
            st.text_input("New name:",
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

        #indices_list_view()

        indices_selector()

        rename_index_component()

    except Exception as e:
        st.error(e)
