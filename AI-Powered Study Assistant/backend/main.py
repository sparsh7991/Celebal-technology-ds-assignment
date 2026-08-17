from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import (
    Conversation,
    Document,
    Message,
    QuizAttempt,
    StudyEvent,
    get_db,
    init_db,
)
from rag_service import DATA_DIR, RAGService


init_db()
rag = RAGService()

app = FastAPI(
    title="AI-Powered Study Assistant API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    document_id: int
    question: str
    conversation_id: int | None = None


class LearningRequest(BaseModel):
    document_id: int
    topic: str | None = None


class ProgressRequest(BaseModel):
    document_id: int | None = None
    topic: str
    event_type: str
    score: float | None = None


class QuizAttemptRequest(BaseModel):
    document_id: int | None = None
    topic: str | None = None
    score: float
    total: int


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/documents")
def get_documents(db: Session = Depends(get_db)):
    rows = (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .all()
    )

    return [
        {
            "id": row.id,
            "filename": row.filename,
            "status": row.status,
            "page_count": row.page_count,
            "chunk_count": row.chunk_count,
            "error_message": row.error_message,
        }
        for row in rows
    ]


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is missing.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    safe_name = Path(file.filename).name
    file_path = DATA_DIR / safe_name

    try:
        with file_path.open("wb") as output:
            shutil.copyfileobj(file.file, output)

        document = Document(
            filename=safe_name,
            path=str(file_path),
            status="indexing",
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        try:
            stats = rag.build_index(
                document.id,
                str(file_path),
            )

            document.status = "indexed"
            document.page_count = stats["pages"]
            document.chunk_count = stats["chunks"]

            db.commit()

        except Exception as exc:
            document.status = "failed"
            document.error_message = str(exc)[:1000]
            db.commit()

            raise HTTPException(
                status_code=422,
                detail=f"Indexing failed: {document.error_message}",
            )

        return {
            "id": document.id,
            "filename": document.filename,
            "status": document.status,
            "page_count": document.page_count,
            "chunk_count": document.chunk_count,
        }

    except HTTPException:
        raise

    except Exception as exc:
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {exc}",
        )


@app.get("/api/documents/{document_id}/view")
def view_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    pdf_path = Path(document.path)

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="PDF file is missing.",
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=document.filename,
        content_disposition_type="inline",
    )


@app.delete("/api/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    rag.delete_document(
        document.id,
        document.path,
    )

    db.delete(document)
    db.commit()

    return {"ok": True}


@app.post("/api/chat")
def chat(
    request: QueryRequest,
    db: Session = Depends(get_db),
):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    document = db.get(Document, request.document_id)

    if not document or document.status != "indexed":
        raise HTTPException(
            status_code=400,
            detail="Selected document is not ready.",
        )

    conversation = None

    if request.conversation_id:
        conversation = db.get(
            Conversation,
            request.conversation_id,
        )

    if conversation is None:
        conversation = Conversation(
            title=question[:60],
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    db.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=question,
        )
    )

    db.commit()

    try:
        result = rag.query(
            document.id,
            question,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {exc}",
        )

    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
        )
    )

    db.add(
        StudyEvent(
            document_id=document.id,
            topic=question[:120],
            event_type="question",
        )
    )

    db.commit()

    return {
        "conversation_id": conversation.id,
        **result,
    }


@app.get("/api/conversations")
def get_conversations(
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Conversation)
        .order_by(Conversation.created_at.desc())
        .all()
    )

    return [
        {
            "id": row.id,
            "title": row.title,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@app.get("/api/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    return [
        {
            "id": row.id,
            "role": row.role,
            "content": row.content,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@app.post("/api/learning/{mode}")
def generate_learning(
    mode: str,
    request: LearningRequest,
    db: Session = Depends(get_db),
):
    if mode not in {"summary", "flashcards", "quiz"}:
        raise HTTPException(
            status_code=404,
            detail="Unknown learning mode.",
        )

    document = db.get(
        Document,
        request.document_id,
    )

    if not document or document.status != "indexed":
        raise HTTPException(
            status_code=400,
            detail="Selected document is not ready.",
        )

    try:
        result = rag.generate_learning(
            document.id,
            mode,
            request.topic,
        )

        db.add(
            StudyEvent(
                document_id=document.id,
                topic=request.topic or "General",
                event_type=mode,
            )
        )

        db.commit()

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{mode} generation failed: {exc}",
        )


@app.post("/api/quiz-attempts")
def save_quiz_attempt(
    request: QuizAttemptRequest,
    db: Session = Depends(get_db),
):
    if request.total <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quiz total must be greater than zero.",
        )

    attempt = QuizAttempt(
        document_id=request.document_id,
        topic=request.topic,
        score=request.score,
        total=request.total,
    )

    db.add(attempt)

    db.add(
        StudyEvent(
            document_id=request.document_id,
            topic=request.topic or "General",
            event_type="quiz_attempt",
            score=request.score,
        )
    )

    db.commit()

    return {"ok": True}


@app.post("/api/progress")
def save_progress(
    request: ProgressRequest,
    db: Session = Depends(get_db),
):
    db.add(
        StudyEvent(
            document_id=request.document_id,
            topic=request.topic,
            event_type=request.event_type,
            score=request.score,
        )
    )

    db.commit()

    return {"ok": True}


@app.get("/api/progress")
def get_progress(
    db: Session = Depends(get_db),
):
    events = (
        db.query(StudyEvent)
        .order_by(StudyEvent.created_at.desc())
        .all()
    )

    quizzes = (
        db.query(QuizAttempt)
        .order_by(QuizAttempt.created_at.desc())
        .all()
    )

    topic_map = {}

    for event in events:
        topic_map.setdefault(
            event.topic,
            {
                "events": 0,
                "last_activity": event.created_at,
            },
        )

        topic_map[event.topic]["events"] += 1

    quiz_average = None

    if quizzes:
        percentages = [
            (quiz.score / max(quiz.total, 1)) * 100
            for quiz in quizzes
        ]

        quiz_average = round(
            sum(percentages) / len(percentages),
            1,
        )

    return {
        "topics": [
            {
                "topic": topic,
                **data,
            }
            for topic, data in sorted(
                topic_map.items(),
                key=lambda item: item[1]["events"],
                reverse=True,
            )
        ],
        "quiz_average": quiz_average,
        "quiz_attempts": len(quizzes),
        "study_events": len(events),
    }


@app.get("/api/evaluation/{document_id}")
def evaluate_rag(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = db.get(
        Document,
        document_id,
    )

    if not document or document.status != "indexed":
        raise HTTPException(
            status_code=404,
            detail="Document not found or not indexed.",
        )

    # Replace these with human-verified questions for a formal benchmark.
    test_cases = [
        "What is the main topic of this document?",
        "List one important concept from the document.",
        "Give one definition stated in the material.",
    ]

    retrieval_hits = 0
    faithfulness_scores = []
    details = []

    for question in test_cases:
        try:
            result = rag.query(
                document_id,
                question,
                top_k=5,
            )

            answer_tokens = set(
                result["answer"].lower().split()
            )

            context_tokens = set(
                " ".join(
                    source["text"]
                    for source in result["sources"]
                ).lower().split()
            )

            overlap = (
                len(answer_tokens & context_tokens)
                / max(len(answer_tokens), 1)
            )

            faithfulness = round(
                min(overlap, 1.0),
                3,
            )

            retrieval_ok = len(result["sources"]) > 0

            retrieval_hits += int(retrieval_ok)
            faithfulness_scores.append(
                faithfulness
            )

            details.append(
                {
                    "question": question,
                    "retrieval_hit": retrieval_ok,
                    "faithfulness": faithfulness,
                }
            )

        except Exception as exc:
            details.append(
                {
                    "question": question,
                    "error": str(exc),
                }
            )

    total = len(test_cases)

    return {
        "retrieval_hit_at_5": round(
            retrieval_hits / max(total, 1),
            3,
        ),
        "answer_faithfulness": round(
            sum(faithfulness_scores)
            / max(len(faithfulness_scores), 1),
            3,
        ),
        "details": details,
        "note": (
            "This is a lightweight local smoke evaluation. "
            "For a formal benchmark, use human-verified questions, "
            "expected evidence and reference answers."
        ),
    }
