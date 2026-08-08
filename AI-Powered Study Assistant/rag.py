import os
import shutil
import fitz

from llama_index.core import (
    Document,
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
)

from llama_index.core.node_parser import SentenceSplitter


class RAG:

    def __init__(self):
        self.index = None
        self.current_document = None

    def _get_storage_path(self, pdf_path):
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        return os.path.join("storage", pdf_name)

    def build_index(self, pdf_path):

        storage_path = self._get_storage_path(pdf_path)
        os.makedirs(storage_path, exist_ok=True)

        pdf = fitz.open(pdf_path)

        text = ""

        for page in pdf:
            text += page.get_text()

        pdf.close()

        documents = [
            Document(
                text=text,
                metadata={
                    "file_name": os.path.basename(pdf_path)
                }
            )
        ]

        splitter = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=50
        )

        nodes = splitter.get_nodes_from_documents(documents)

        self.index = VectorStoreIndex(nodes)

        self.index.storage_context.persist(
            persist_dir=storage_path
        )

        self.current_document = pdf_path

    def load_index(self, pdf_path):

        storage_path = self._get_storage_path(pdf_path)

        storage_context = StorageContext.from_defaults(
            persist_dir=storage_path
        )

        self.index = load_index_from_storage(
            storage_context
        )

        self.current_document = pdf_path

    def query(self, question):

        if self.index is None:
            raise Exception("No document selected.")

        query_engine = self.index.as_query_engine(
            similarity_top_k=5
        )

        response = query_engine.query(question)

        return str(response)

    def document_exists(self, pdf_path):

        storage_path = self._get_storage_path(pdf_path)

        return (
            os.path.exists(storage_path)
            and len(os.listdir(storage_path)) > 0
        )

    def get_uploaded_documents(self):

        if not os.path.exists("data"):
            return []

        return sorted(
            [
                file
                for file in os.listdir("data")
                if file.lower().endswith(".pdf")
            ]
        )

    def get_current_document(self):

        if self.current_document is None:
            return None

        return os.path.basename(self.current_document)

    def get_document_path(self, pdf_name):

        return os.path.join(
            "data",
            pdf_name
        )

    def delete_document(self, pdf_name):

        pdf_path = os.path.join(
            "data",
            pdf_name
        )

        storage_path = os.path.join(
            "storage",
            os.path.splitext(pdf_name)[0]
        )

        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        if os.path.exists(storage_path):
            shutil.rmtree(storage_path)

        if (
            self.current_document is not None
            and os.path.basename(self.current_document) == pdf_name
        ):
            self.current_document = None
            self.index = None