"use client";

import { useEffect, useState } from "react";

const API = "http://localhost:8000/api";

type Document = {
  id: number;
  filename: string;
  status: string;
  page_count: number;
  chunk_count: number;
  error_message?: string | null;
};

type Source = {
  page: number;
  file: string;
  score: number;
  text: string;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
};

type Flashcard = {
  question: string;
  answer: string;
};

type QuizQuestion = {
  question: string;
  options: string[];
  answer: number;
  explanation: string;
};

type Progress = {
  quiz_average: number | null;
  quiz_attempts: number;
  study_events: number;
  topics: {
    topic: string;
    events: number;
  }[];
};

export default function Home() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);

  const [mode, setMode] = useState<
    "chat" | "watch" | "summary" | "flashcards" | "quiz" | "progress"
  >("chat");

  const [generated, setGenerated] = useState<
    string | Flashcard[] | QuizQuestion[] | null
  >(null);

  const [progress, setProgress] = useState<Progress | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const current = docs.find((doc) => doc.id === selected);

  async function loadDocuments() {
    try {
      const response = await fetch(`${API}/documents`);
      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}.`);
      }
      setDocs(await response.json());
    } catch (err) {
      setError(
        err instanceof Error
          ? `Backend connection failed: ${err.message}`
          : "Backend connection failed. Start FastAPI on port 8000."
      );
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  function selectDocument(id: number) {
    setSelected(id);
    setMessages([]);
    setConversationId(null);
    setGenerated(null);
    setMode("chat");
    setError("");
  }

  async function uploadPDF(file: File) {
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(
        `${API}/documents/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "PDF upload/indexing failed."
        );
      }

      await loadDocuments();
      selectDocument(data.id);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "PDF upload failed."
      );
    }
  }

  async function askQuestion() {
    if (!selected || !question.trim() || loading) {
      return;
    }

    const userQuestion = question.trim();

    setQuestion("");
    setError("");
    setLoading(true);

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: userQuestion,
      },
    ]);

    try {
      const response = await fetch(
        `${API}/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            document_id: selected,
            question: userQuestion,
            conversation_id: conversationId,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Query failed."
        );
      }

      setConversationId(data.conversation_id);

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
        },
      ]);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Query failed."
      );

    } finally {
      setLoading(false);
    }
  }

  async function generate(
    kind: "summary" | "flashcards" | "quiz"
  ) {
    if (!selected || loading) {
      return;
    }

    setGenerated(null);
    setError("");
    setLoading(true);

    try {
      const response = await fetch(
        `${API}/learning/${kind}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            document_id: selected,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Generation failed."
        );
      }

      setGenerated(data.content);

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Generation failed."
      );

    } finally {
      setLoading(false);
    }
  }

  async function loadProgress() {
    const response = await fetch(
      `${API}/progress`
    );

    if (response.ok) {
      setProgress(await response.json());
    }
  }

  async function deleteDocument(id: number) {
    try {
      const response = await fetch(
        `${API}/documents/${id}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error("Could not delete document.");
      }

      if (selected === id) {
        setSelected(null);
        setMessages([]);
        setGenerated(null);
      }

      await loadDocuments();

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Delete failed."
      );
    }
  }

  function changeMode(
    newMode:
      | "chat"
      | "watch"
      | "summary"
      | "flashcards"
      | "quiz"
      | "progress"
  ) {
    setMode(newMode);
    setGenerated(null);

    if (newMode === "progress") {
      loadProgress();
    }
  }

  return (
    <main className="app">
      <aside className="sidebar">
        <div className="brand">
          📚 Study Assistant
        </div>

        <p className="muted">
          Local RAG • persistent learning
        </p>

        <label className="upload">
          <span>＋ Upload PDF</span>

          <input
            type="file"
            accept=".pdf"
            onChange={(event) => {
              const file = event.target.files?.[0];

              if (file) {
                uploadPDF(file);
              }

              event.currentTarget.value = "";
            }}
          />
        </label>

        <div className="side-title">
          Documents
        </div>

        {docs.length === 0 && (
          <p className="muted">
            No PDFs uploaded yet.
          </p>
        )}

        {docs.map((doc) => (
          <div
            className={`doc ${
              selected === doc.id
                ? "active"
                : ""
            }`}
            key={doc.id}
          >
            <button
              className="docButton"
              onClick={() =>
                selectDocument(doc.id)
              }
            >
              <b>{doc.filename}</b>

              <small>
                {doc.page_count} pages •{" "}
                {doc.status}
              </small>
            </button>

            <button
              className="delete"
              onClick={() =>
                deleteDocument(doc.id)
              }
            >
              ×
            </button>
          </div>
        ))}
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <h1>
              {current
                ? current.filename
                : "Your study workspace"}
            </h1>

            <p>
              {current
                ? `${current.page_count} pages • ${current.chunk_count} indexed chunks`
                : "Upload a PDF to start learning."}
            </p>
          </div>

          <nav className="tabs">
            {[
              "chat",
              "watch",
              "summary",
              "flashcards",
              "quiz",
              "progress",
            ].map((item) => (
              <button
                key={item}
                className={
                  mode === item
                    ? "selectedTab"
                    : ""
                }
                onClick={() =>
                  changeMode(
                    item as typeof mode
                  )
                }
              >
                {item[0].toUpperCase() +
                  item.slice(1)}
              </button>
            ))}
          </nav>
        </header>

        {error && (
          <div className="error">
            ⚠️ {error}
          </div>
        )}

        {!selected ? (
          <section className="empty">
            <div className="emptyIcon">
              🧠
            </div>

            <h2>
              Study smarter, not harder.
            </h2>

            <p>
              Upload your notes or textbook PDF
              and ask questions, generate
              revision material, and track
              learning progress.
            </p>
          </section>
        ) : mode === "chat" ? (
          <>
            <section className="chat">
              {messages.length === 0 && (
                <div className="hint">
                  Ask anything from{" "}
                  <b>{current?.filename}</b>.
                  Answers include retrieved
                  PDF pages.
                </div>
              )}

              {messages.map(
                (message, index) => (
                  <div
                    key={index}
                    className={`message ${message.role}`}
                  >
                    <div className="bubble">
                      {message.content}
                    </div>

                    {message.sources && (
                      <div className="sources">
                        <b>
                          Retrieved sources
                        </b>

                        {message.sources.map(
                          (
                            source,
                            sourceIndex
                          ) => (
                            <div
                              className="source"
                              key={
                                sourceIndex
                              }
                            >
                              <span>
                                📄{" "}
                                {
                                  source.file
                                }{" "}
                                • Page{" "}
                                {
                                  source.page
                                }{" "}
                                • score{" "}
                                {
                                  source.score
                                }
                              </span>

                              <p>
                                {
                                  source.text
                                }
                              </p>
                            </div>
                          )
                        )}
                      </div>
                    )}
                  </div>
                )
              )}

              {loading && (
                <div className="bubble assistant">
                  Thinking…
                </div>
              )}
            </section>

            <div className="composer">
              <input
                value={question}
                onChange={(event) =>
                  setQuestion(
                    event.target.value
                  )
                }
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter"
                  ) {
                    askQuestion();
                  }
                }}
                placeholder="Ask something from your material…"
              />

              <button
                onClick={askQuestion}
                disabled={loading}
              >
                Ask
              </button>
            </div>
          </>
        ) : mode === "watch" ? (
          <section className="watchPanel">
            <div className="watchHeader">
              <div>
                <h2>👀 Watch / Read Document</h2>
                <p>
                  Read the original PDF without leaving the Study Assistant.
                  Use the browser PDF controls to zoom, search, and move between pages.
                </p>
              </div>

              <a
                className="openPdf"
                href={`${API}/documents/${selected}/view`}
                target="_blank"
                rel="noreferrer"
              >
                Open in new tab ↗
              </a>
            </div>

            <div className="pdfViewer">
              <iframe
                src={`${API}/documents/${selected}/view`}
                title={current?.filename ?? "Study document"}
              />
            </div>
          </section>
        ) : mode === "progress" ? (
          <section className="panel">
            <div className="featureHead">
              <div>
                <h2>
                  📈 Learning Progress
                </h2>

                <p>
                  Persistent study activity
                  stored in SQLite.
                </p>
              </div>

              <button
                onClick={loadProgress}
              >
                Refresh
              </button>
            </div>

            {progress && (
              <>
                <div className="stats">
                  <div>
                    <b>
                      {progress.quiz_average ??
                        "—"}
                      %
                    </b>

                    <span>
                      Quiz average
                    </span>
                  </div>

                  <div>
                    <b>
                      {
                        progress.quiz_attempts
                      }
                    </b>

                    <span>
                      Quiz attempts
                    </span>
                  </div>

                  <div>
                    <b>
                      {
                        progress.study_events
                      }
                    </b>

                    <span>
                      Study activities
                    </span>
                  </div>
                </div>

                <h3>
                  Topics / activities
                </h3>

                {progress.topics.map(
                  (topic) => (
                    <div
                      className="topic"
                      key={topic.topic}
                    >
                      <span>
                        {topic.topic}
                      </span>

                      <b>
                        {topic.events}
                      </b>
                    </div>
                  )
                )}
              </>
            )}
          </section>
        ) : (
          <section className="panel">
            <div className="featureHead">
              <div>
                <h2>
                  {mode === "summary"
                    ? "📝 Smart Summary"
                    : mode ===
                        "flashcards"
                      ? "🗂️ Flashcards"
                      : "🧪 Quiz Generator"}
                </h2>

                <p>
                  Generated from your
                  indexed study material.
                </p>
              </div>

              <button
                onClick={() =>
                  generate(mode)
                }
                disabled={loading}
              >
                {loading
                  ? "Generating…"
                  : "Generate"}
              </button>
            </div>

            {mode === "summary" &&
              typeof generated ===
                "string" && (
                <pre className="summary">
                  {generated}
                </pre>
              )}

            {mode === "flashcards" &&
              Array.isArray(
                generated
              ) && (
                <div className="cards">
                  {(
                    generated as Flashcard[]
                  ).map(
                    (card, index) => (
                      <details
                        key={index}
                      >
                        <summary>
                          {card.question}
                        </summary>

                        <p>
                          {card.answer}
                        </p>
                      </details>
                    )
                  )}
                </div>
              )}

            {mode === "quiz" &&
              Array.isArray(
                generated
              ) && (
                <Quiz
                  questions={
                    generated as QuizQuestion[]
                  }
                  documentId={selected}
                />
              )}
          </section>
        )}
      </section>
    </main>
  );
}


function Quiz({
  questions,
  documentId,
}: {
  questions: QuizQuestion[];
  documentId: number;
}) {
  const [answers, setAnswers] =
    useState<Record<number, number>>({});

  const [result, setResult] =
    useState<number | null>(null);

  async function submitQuiz() {
    let score = 0;

    questions.forEach(
      (question, index) => {
        if (
          answers[index] ===
          question.answer
        ) {
          score++;
        }
      }
    );

    setResult(score);

    await fetch(
      `${API}/quiz-attempts`,
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify({
          document_id: documentId,
          score,
          total: questions.length,
        }),
      }
    );
  }

  return (
    <div className="quiz">
      {questions.map(
        (question, index) => (
          <div
            className="q"
            key={index}
          >
            <b>
              {index + 1}.{" "}
              {question.question}
            </b>

            {question.options.map(
              (option, optionIndex) => (
                <label
                  key={optionIndex}
                >
                  <input
                    type="radio"
                    name={`q-${index}`}
                    checked={
                      answers[index] ===
                      optionIndex
                    }
                    onChange={() =>
                      setAnswers(
                        (previous) => ({
                          ...previous,
                          [index]:
                            optionIndex,
                        })
                      )
                    }
                  />

                  {option}
                </label>
              )
            )}

            {result !== null && (
              <small>
                {answers[index] ===
                question.answer
                  ? "✅ Correct"
                  : `❌ Correct answer: ${question.options[question.answer]}`}
                {" — "}
                {
                  question.explanation
                }
              </small>
            )}
          </div>
        )
      )}

      <button
        onClick={submitQuiz}
      >
        Submit Quiz
      </button>

      {result !== null && (
        <h3>
          Score: {result}/
          {questions.length}
        </h3>
      )}
    </div>
  );
}
