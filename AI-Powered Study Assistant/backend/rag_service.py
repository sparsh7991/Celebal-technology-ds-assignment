from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import fitz
from llama_index.core import Document, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter

import config  # noqa: F401


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / "storage"
DATA_DIR.mkdir(exist_ok=True)
INDEX_DIR.mkdir(exist_ok=True)


class RAGService:
    def _storage_path(self, document_id: int) -> Path:
        return INDEX_DIR / f"document_{document_id}"

    def build_index(self, document_id: int, pdf_path: str) -> dict:
        pdf = None
        try:
            pdf = fitz.open(pdf_path)

            if pdf.page_count == 0:
                raise ValueError("The PDF contains no pages.")

            documents = []

            for page_number in range(pdf.page_count):
                page = pdf.load_page(page_number)
                text = page.get_text("text").strip()

                if not text:
                    continue

                documents.append(
                    Document(
                        text=text,
                        metadata={
                            "document_id": document_id,
                            "file_name": Path(pdf_path).name,
                            "page_number": page_number + 1,
                        },
                    )
                )

            if not documents:
                raise ValueError(
                    "No extractable text was found. The PDF may be scanned/image-only."
                )

            splitter = SentenceSplitter(
                chunk_size=350,
                chunk_overlap=40,
            )

            nodes = splitter.get_nodes_from_documents(documents)

            storage_path = self._storage_path(document_id)

            if storage_path.exists():
                shutil.rmtree(storage_path)

            index = VectorStoreIndex(nodes)
            index.storage_context.persist(persist_dir=str(storage_path))

            return {
                "pages": pdf.page_count,
                "chunks": len(nodes),
            }

        finally:
            if pdf is not None:
                pdf.close()

    def load_index(self, document_id: int):
        storage_path = self._storage_path(document_id)

        if not storage_path.exists():
            raise FileNotFoundError("Vector index not found for this document.")

        storage_context = StorageContext.from_defaults(
            persist_dir=str(storage_path)
        )

        return load_index_from_storage(storage_context)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z0-9]{3,}", text.lower()))

    def _rewrite_query(self, question: str) -> str:
        try:
            from llama_index.core import Settings

            prompt = (
                "Rewrite this student question into one concise semantic search query. "
                "Preserve the meaning. Return only the rewritten query.\n\n"
                f"Question: {question}"
            )

            rewritten = str(Settings.llm.complete(prompt)).strip()

            if rewritten and len(rewritten) <= 500:
                return rewritten

        except Exception:
            pass

        return question

    def query(self, document_id: int, question: str, top_k: int = 5) -> dict:
        index = self.load_index(document_id)

        # Rewrite only for retrieval; keep the user's original question for the answer.
        rewritten_query = self._rewrite_query(question)
        retriever = index.as_retriever(similarity_top_k=max(top_k, 10))
        retrieved = retriever.retrieve(rewritten_query)

        # Hybrid retrieval: semantic similarity + lexical overlap with BOTH
        # the original and rewritten query. This prevents generic chunks from
        # winning when the user asks for a specific section such as "projects".
        query_tokens = self._tokens(f"{question} {rewritten_query}")
        ranked = []

        for item in retrieved:
            text = item.node.get_content()
            semantic_score = max(float(item.score or 0.0), 0.0)
            text_tokens = self._tokens(text)
            overlap = len(query_tokens & text_tokens) / max(len(query_tokens), 1)
            final_score = 0.60 * semantic_score + 0.40 * min(overlap, 1.0)
            ranked.append((final_score, item))

        ranked.sort(key=lambda pair: pair[0], reverse=True)
        selected = ranked[:top_k]

        context = "\n\n".join(
            f"[S{i + 1} | Page {item.node.metadata.get('page_number', '?')}]\n"
            f"{item.node.get_content()}"
            for i, (_, item) in enumerate(selected)
        )

        from llama_index.core import Settings
        prompt = (
            "You are an AI study assistant. Answer ONLY using the supplied sources. "
            "Do not use outside knowledge. If the sources do not support the answer, "
            "say so. Keep the answer concise.\n\n"
            f"Sources:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

        answer = str(Settings.llm.complete(prompt)).strip()

        # After generation, rank evidence against the ACTUAL answer as well.
        # This fixes the common case where the answer is right but the top
        # semantic chunks are generic and do not visibly support it.
        evidence_tokens = self._tokens(f"{question} {answer}")
        evidence_ranked = []
        for score, item in selected:
            text_tokens = self._tokens(item.node.get_content())
            evidence_overlap = len(evidence_tokens & text_tokens) / max(len(evidence_tokens), 1)
            evidence_score = 0.55 * score + 0.45 * evidence_overlap
            evidence_ranked.append((evidence_score, item))

        evidence_ranked.sort(key=lambda pair: pair[0], reverse=True)

        sources = [
            {
                "page": item.node.metadata.get("page_number"),
                "file": item.node.metadata.get("file_name"),
                "score": round(float(score), 4),
                "text": item.node.get_content()[:900],
            }
            for score, item in evidence_ranked[: min(top_k, 4)]
        ]

        return {
            "answer": answer,
            "rewritten_query": rewritten_query,
            "sources": sources,
        }

    def generate_learning(
        self,
        document_id: int,
        mode: str,
        topic: str | None = None,
    ):
        index = self.load_index(document_id)
        query = topic or "main concepts important definitions formulas key ideas and important facts"

        # Fewer chunks = much smaller prompts and faster local generation.
        retriever = index.as_retriever(similarity_top_k=5)
        retrieved = retriever.retrieve(query)

        context = "\n\n".join(
            f"[Page {item.node.metadata.get('page_number', '?')}]\n{item.node.get_content()}"
            for item in retrieved
        )

        from llama_index.core import Settings

        if mode == "summary":
            prompt = (
                "Summarize ONLY the supplied study material. Use 5-8 concise bullet points "
                "and a short revision checklist. Do not add facts that are not in the material.\n\n"
                f"Material:\n{context}\n\nSummary:"
            )
            return {"content": str(Settings.llm.complete(prompt)).strip()}

        if mode == "flashcards":
            # Plain text is deliberately used instead of JSON because small local models
            # frequently produce malformed JSON. The parser below accepts this format.
            prompt = (
                "Create exactly 6 study flashcards using ONLY facts explicitly present in the material. "
                "Do not invent facts. Use this exact format and nothing else:\n"
                "CARD 1\nQ: question\nA: answer\n"
                "CARD 2\nQ: question\nA: answer\n"
                "...\n\n"
                f"Material:\n{context}\n\nFlashcards:\n"
            )
            raw = str(Settings.llm.complete(prompt)).strip()
            cards = self._parse_flashcards(raw)
            return {"content": cards}

        if mode == "quiz":
            prompt = (
                "Create exactly 4 multiple-choice questions using ONLY facts explicitly present in the material. "
                "Every correct answer MUST be directly supported by the material. "
                "Do not use outside knowledge. Make the correct option different across questions. "
                "Use this exact format:\n"
                "QUESTION 1: ...\nA) ...\nB) ...\nC) ...\nD) ...\nANSWER: A\nEXPLANATION: ...\n\n"
                "QUESTION 2: ... and so on.\n\n"
                f"Material:\n{context}\n\nQuiz:\n"
            )
            raw = str(Settings.llm.complete(prompt)).strip()
            questions = self._parse_quiz(raw)
            return {"content": questions}

        raise ValueError("Unsupported learning mode.")

    @staticmethod
    def _parse_flashcards(raw: str) -> list[dict]:
        cards = []
        pattern = re.compile(
            r"(?:CARD\s*\d+\s*)?Q\s*:\s*(.*?)\s*A\s*:\s*(.*?)(?=\n\s*(?:CARD\s*\d+\s*)?Q\s*:|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(raw):
            question = " ".join(match.group(1).split())
            answer = " ".join(match.group(2).split())
            if question and answer:
                cards.append({"question": question, "answer": answer})
        return cards[:6]

    @staticmethod
    def _parse_quiz(raw: str) -> list[dict]:
        blocks = re.split(r"(?=QUESTION\s*\d+\s*:)", raw, flags=re.IGNORECASE)
        result = []
        for block in blocks:
            q = re.search(r"QUESTION\s*\d+\s*:\s*(.*?)(?=\n\s*A\)\s*)", block, re.I | re.S)
            options = re.findall(r"^\s*([A-D])\)\s*(.*?)\s*$", block, re.I | re.M)
            ans = re.search(r"ANSWER\s*:\s*([A-D])", block, re.I)
            exp = re.search(r"EXPLANATION\s*:\s*(.*)$", block, re.I | re.S)
            if not q or len(options) != 4 or not ans:
                continue
            letters = [x[0].upper() for x in options]
            if ans.group(1).upper() not in letters:
                continue
            answer_index = letters.index(ans.group(1).upper())
            result.append({
                "question": " ".join(q.group(1).split()),
                "options": [" ".join(x[1].split()) for x in options],
                "answer": answer_index,
                "explanation": " ".join(exp.group(1).split()) if exp else "",
            })
        return result[:4]

    @staticmethod
    def _safe_json(raw: str, fallback):
        try:
            if "```" in raw:
                parts = raw.split("```")

                if len(parts) >= 2:
                    raw = parts[1]

                raw = raw.replace("json", "", 1).strip()

            return json.loads(raw)

        except Exception:
            return fallback

    def delete_document(self, document_id: int, pdf_path: str):
        storage_path = self._storage_path(document_id)

        if storage_path.exists():
            shutil.rmtree(storage_path)

        Path(pdf_path).unlink(missing_ok=True)
