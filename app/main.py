import base64
import os
from typing import Any

import requests
import streamlit as st
from streamlit_tree_select import tree_select
from config import Settings

st.set_page_config(layout="wide")

settings = Settings()

st.header(
    "Sample Choreo RAG application",
    anchor=None,
    help=None,
    divider="grey",
)


def populate_documents(
    collections: list[dict[str, str, list[Any]] | None]
) -> list[dict[str, str, None | list[Any]]]:
    try:
        for collecion in collections:
            resp = requests.get(
                f"{settings.backend_base_path}/collection/{collecion['value']}",
                params={"with_documents": True},
                timeout=12000
            ).json()

            if "documents" in resp:
                doc_list = resp["documents"]
                if doc_list and len(doc_list) > 0:
                    children: list[dict[str, Any]] = []
                    for doc in doc_list:
                        children.append(
                            {"label": doc, "value": doc, "showCheckbox": False})
                    collecion["children"] = children
        return collections
    except:
        return None


def get_collections(populate_docs: bool = False) -> list[dict[str, str, None | list[Any]]]:
    collections: list[dict[str, str, list[Any]] | None] = []

    def get_data():
        url = f"{settings.backend_base_path}/collection/list"
        page_size = 10
        session = requests.session()
        first_page = session.get(
            url,
            params={"page": 1, "size": page_size}
        ).json()
        yield first_page

        total_pages = first_page["meta"]["total_pages"]

        for i in range(2, total_pages + 1):
            next_page = session.get(
                url,
                params={"page": i, "size": page_size}
            ).json()
            yield next_page

    try:
        for page in get_data():
            if "colelctions" in page:
                for collection in page["collections"]:
                    collections.append(
                        {
                            "label": collection["name"].capitalize(),
                            "value": collection["uuid"],
                            "showCheckbox": False
                        }
                    )

        if populate_docs:
            return populate_documents(collections)
        collections.sort(key=lambda c: c["label"])
    finally:
        return collections


def __format_response_markdown(json_resp) -> tuple[str, set | None]:
    result = "I don't know the answer for the question you asked"
    sources: list[tuple[str, int]] = []
    if "result" in json_resp:
        result = f"{json_resp['result']}"

    if "citations" in json_resp:
        for source in json_resp["citations"]:
            sources.append({source["document"], source["page"]})
        return result, set(sources)
    else:
        return result, None


def get_assistance_response(
    selected_collection, selected_document, prompt: str
) -> tuple[str, set | None]:
    def qa(mode: str, identifier: str):
        try:
            response = requests.post(
                url=f"{settings.backend_base_path}/chat",
                json={
                    "mode": mode,
                    "id_type": "name",
                    "identifier": identifier,
                    "query": prompt,
                    "llm": {
                        "temperature": 0,
                        "max_tokens": 200,
                        "logit_bias": {"50256": -100},
                    },
                    "include_citations": True,
                    "include_usage": False,
                },
            )
            if response.status_code == 200:
                return __format_response_markdown(response.json())
            else:
                raise Exception("Error response received")
        except Exception:
            return "**Error occurred while generating the response**", None

    if selected_document is None:
        return qa("collection", selected_collection["label"])
    else:
        return qa("document", selected_document["label"])


def upload_document(collection: str, document) -> requests.Response:
    return requests.post(
        url=f"{settings.backend_base_path}/document/upload",
        data={"collection": collection},
        files=[("file", (document.name, document.getvalue()))],
    )


def submitted():
    st.session_state.submitted = True


def reset():
    st.session_state.submitted = False


def refresh_sidebar():
    collections = get_collections(populate_docs=True)

    with st.sidebar:
        tree_container = st.container()
        form_container = st.container()
        with tree_container:
            st.header(
                "Documents",
                anchor=None,
                help=None,
                divider="rainbow",
            )
            tree_select(nodes=collections, expand_on_click=True,
                        show_expand_all=True)

        with form_container:
            st.header(
                "Add Document",
                anchor=None,
                help=None,
                divider="rainbow",
            )
            with st.form(key="add_doc_form", clear_on_submit=True):
                doc_collection = st.text_input("Collection")
                doc = st.file_uploader(
                    label="Choose a PDF file", accept_multiple_files=False
                )
                st.form_submit_button("Add Document", on_click=submitted)

    if "submitted" in st.session_state and st.session_state.submitted:
        if doc and doc_collection:
            resp = upload_document(doc_collection, doc)

            if resp.status_code == 200:
                refresh_sidebar()


def display_chat(container, message, role):
    with container:
        with st.chat_message(role):
            st.markdown(message)


def display_sources(container, sources: set[tuple[str, int]]):
    with container:
        st.header("Sources:", divider="grey")
        for source in sources:
            with st.expander(f"{source[0].split(os.sep)[-1]}, page: {source[1] + 1}"):
                with open(source[0], "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode("utf-8")
                pdf_display = f"""<embed src="data:application/pdf;base64,{base64_pdf}#page={source[1] + 1}" \
                width="800" height="800" type="application/pdf"></embed>"""

                st.markdown(pdf_display, unsafe_allow_html=True)


def main():
    refresh_sidebar()

    chat_select_container = st.container()
    collections = get_collections(populate_docs=True)
    with chat_select_container:
        col1, col2 = st.columns(2)
        with col1:
            selected_collection = st.selectbox(
                "Select the Collection:",
                collections,
                format_func=lambda collection: collection["label"].capitalize(
                ),
            )
        with col2:
            selected_document = st.selectbox(
                "Filter by document:",
                selected_collection["children"],
                format_func=lambda document: document["label"].capitalize(),
                index=None,
                placeholder="Filter by document",
            )

    chat_container = st.container()

    with chat_container:
        chat_col, sources_col = st.columns([5, 2])
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with chat_col:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question"):
        sources_col.empty()
        st.session_state.messages.append({"role": "user", "content": prompt})
        display_chat(chat_col, prompt, "user")

        assistant_response, sources = get_assistance_response(
            selected_collection, selected_document, prompt
        )

        display_chat(chat_col, assistant_response, "assistant")
        display_sources(sources_col, sources)

        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_response}
        )


if __name__ == "__main__":
    main()
