import os
import streamlit as st
from rag import RAG

st.set_page_config(
    page_title="AI-Powered Study Assistant",
    page_icon="📚",
    layout="wide"
)

if "rag" not in st.session_state:
    st.session_state.rag = RAG()

rag = st.session_state.rag

os.makedirs("data", exist_ok=True)
os.makedirs("storage", exist_ok=True)
os.makedirs("sessions", exist_ok=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "selected_doc" not in st.session_state:
    st.session_state.selected_doc = None

if "view_pdf" not in st.session_state:
    st.session_state.view_pdf = None

st.title("📚 AI-Powered Study Assistant")

# ---------------- Sidebar ---------------- #

st.sidebar.title("📚 Documents")

uploaded_docs = rag.get_uploaded_documents()

uploaded_file = st.sidebar.file_uploader(
    "Upload PDF",
    type=["pdf"]
)

if uploaded_file:

    file_path = os.path.join(
        "data",
        uploaded_file.name
    )

    if not os.path.exists(file_path):

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        with st.spinner("Creating Index..."):
            rag.build_index(file_path)

        st.sidebar.success("Indexed Successfully!")

        st.rerun()

    else:

        st.sidebar.info("Already Uploaded")

st.sidebar.divider()

st.sidebar.subheader("Uploaded Documents")

for doc in uploaded_docs:

    col1, col2, col3 = st.sidebar.columns([6,1,1])

    if col1.button(
        doc,
        key=f"load_{doc}",
        use_container_width=True
    ):

        rag.load_index(
            os.path.join("data", doc)
        )

        st.session_state.selected_doc = doc

        st.rerun()

    if col2.button(
        "👁",
        key=f"view_{doc}"
    ):

        st.session_state.view_pdf = rag.get_document_path(doc)

    if col3.button(
        "🗑",
        key=f"delete_{doc}"
    ):

        rag.delete_document(doc)

        st.success(f"{doc} deleted successfully!")

        st.rerun()

# ---------------- Chat ---------------- #

st.subheader("💬 Chat")

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.selected_doc:

    st.success(
        f"Current Document : {st.session_state.selected_doc}"
    )

question = st.chat_input(
    "Ask something..."
)

if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):

        with st.spinner("Thinking..."):

            answer = rag.query(question)

        st.markdown(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )

# ---------------- Footer ---------------- #

st.divider()

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Uploaded PDFs",
        len(uploaded_docs)
    )

with col2:

    current = rag.get_current_document()

    if current:
        st.metric(
            "Current Document",
            current
        )
    else:
        st.metric(
            "Current Document",
            "None"
        )

if st.session_state.view_pdf:

    st.divider()

    st.subheader("📄 PDF Preview")

    with open(st.session_state.view_pdf, "rb") as f:

        pdf_bytes = f.read()

    st.download_button(
        "Open PDF",
        pdf_bytes,
        file_name=os.path.basename(st.session_state.view_pdf),
        mime="application/pdf"
    )