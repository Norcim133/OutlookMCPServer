from llama_index.indices.managed.llama_cloud import LlamaCloudIndex
from llama_index.core.schema import ImageNode, TextNode, NodeWithScore, MetadataMode
import logging
from PIL import Image
import os
import json
import streamlit as st


def llama_retrieval(_nodes_with_scores):
    if _nodes_with_scores is None:
        raise ValueError("_nodes_with_scores cannot be None")
    nodes = []
    for node_with_score in _nodes_with_scores:
        node = node_with_score.node
        score = node_with_score.score
        if isinstance(node, ImageNode):
            image_source = node.resolve_image()
            content = Image.open(image_source)
            node_type = "image"
        else:
            content = node.get_text()
            node_type = "text"
        metadata = node.metadata
        file_id = node.metadata.get('file_id')
        file_url = st.session_state.llama.get_file_content_url(file_id=file_id)
        node_dict = {'metadata': metadata,
                     'type': node_type,
                     'content': content,
                     'url': file_url,
                     'score': score
                    }
        nodes.append(node_dict)
    return nodes
