import streamlit as st

@st.cache_resource
def llama_files_dict():
    llama_files = st.session_state.llama.list_llama_files_dict()
    return llama_files


def file_list():
    llama = st.session_state.llama
    llama_files = llama_files_dict()

    st.header('Data Sources')

    for ds in llama_files['data_sources'].keys():
        with st.expander(ds):
            for folder in llama_files['data_sources'][ds]['folders'].keys():
                st.write(folder)
                for file in llama_files['data_sources'][ds]['folders'][folder]['files']:
                    st.write(file)

    example_file_id = "c17bd7a5-0c32-47d0-91a2-a0c04b4add4c"
    try:
        response = llama.list_file_screenshots(example_file_id)
        st.write(response)
        import asyncio
        @st.cache_resource
        def get_thing(abddd):
            i = llama.get_file_screenshot(abddd, 0)
            return i
        img = get_thing(example_file_id)
        st.image(img)
    except Exception as e:
        st.warning("Failed to retrieve file screenshot: {}".format(str(e)))

    #llama_files = st.session_state.llama.list_available_llama_files(raw_response=True)
    #st.json(llama_files)

def file_manager():
    st.title("File Manager")
    with st.container(border=True):
        file_list()
