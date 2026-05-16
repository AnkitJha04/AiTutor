import { useEffect, useMemo, useState } from "react";

import { postJson } from "./lib/api";

const classOptions = [
  { label: "Class 9", value: "9" },
  { label: "Class 10", value: "10" }
];
const subjectOptions = [
  { label: "Science", value: "science" },
  { label: "Maths", value: "maths" }
];

export default function App() {
  const [className, setClassName] = useState("9");
  const [subject, setSubject] = useState("science");
  const [bookTitle, setBookTitle] = useState("");
  const [topicTitle, setTopicTitle] = useState("");
  const [chapter, setChapter] = useState("");
  const [subtopic, setSubtopic] = useState("");
  const [books, setBooks] = useState([]);
  const [topics, setTopics] = useState([]);
  const [chapters, setChapters] = useState([]);
  const [subtopics, setSubtopics] = useState([]);
  const [notes, setNotes] = useState(null);
  const [questions, setQuestions] = useState(null);
  const [examples, setExamples] = useState(null);
  const [mcqAnswer, setMcqAnswer] = useState("");
  const [shortAnswer, setShortAnswer] = useState("");
  const [longAnswer, setLongAnswer] = useState("");
  const [mcqEvaluation, setMcqEvaluation] = useState(null);
  const [shortEvaluation, setShortEvaluation] = useState(null);
  const [longEvaluation, setLongEvaluation] = useState(null);
  const [status, setStatus] = useState({
    books: "idle",
    topics: "idle",
    chapters: "idle",
    subtopics: "idle",
    notes: "idle",
    questions: "idle",
    examples: "idle",
    evaluationMcq: "idle",
    evaluationShort: "idle",
    evaluationLong: "idle"
  });
  const [error, setError] = useState("");

  const statusMessage = useMemo(() => {
    if (error) return `Error: ${error}`;
    const labels = {
      books: "books",
      chapters: "chapters",
      topics: "topics",
      subtopics: "subtopics",
      notes: "notes",
      questions: "questions",
      examples: "examples",
      evaluationMcq: "MCQ evaluation",
      evaluationShort: "short evaluation",
      evaluationLong: "long evaluation"
    };
    const loadingEntry = Object.entries(status).find(([, value]) => value === "loading");
    if (loadingEntry) {
      const label = labels[loadingEntry[0]] || loadingEntry[0];
      return `Loading ${label}…`;
    }
    return "Idle";
  }, [error, status]);

  const canQuery = useMemo(
    () => bookTitle && chapter && subtopic,
    [bookTitle, chapter, subtopic]
  );

  useEffect(() => {
    let isMounted = true;
    async function loadBooks() {
      setStatus((prev) => ({ ...prev, books: "loading" }));
      setError("");
      try {
        const data = await postJson("/books", { class_name: className, subject });
        if (!isMounted) return;
        const nextBooks = data.books || [];
        setBooks(nextBooks);
        setBookTitle(nextBooks[0] || "");
        setTopics([]);
        setTopicTitle("");
        setChapters([]);
        setChapter("");
        setSubtopics([]);
        setSubtopic("");
      } catch (err) {
        if (!isMounted) return;
        setError(err.message || "Failed to load books");
      } finally {
        if (!isMounted) return;
        setStatus((prev) => ({ ...prev, books: "idle" }));
      }
    }
    loadBooks();
    return () => {
      isMounted = false;
    };
  }, [className, subject]);

  useEffect(() => {
    if (!bookTitle) return;
    let isMounted = true;
    async function loadChapters() {
      setStatus((prev) => ({ ...prev, chapters: "loading" }));
      setError("");
      try {
        const data = await postJson("/chapters", {
          class_name: className,
          subject,
          book_title: bookTitle
        });
        if (!isMounted) return;
        setChapters(data.chapters || []);
        if (data.index_status === "error") {
          setError(data.index_error || "Indexing failed for this book.");
        }
        setChapter("");
        setTopics([]);
        setTopicTitle("");
        setSubtopics([]);
        setSubtopic("");
      } catch (err) {
        if (!isMounted) return;
        setError(err.message || "Failed to load chapters");
      } finally {
        if (!isMounted) return;
        setStatus((prev) => ({ ...prev, chapters: "idle" }));
      }
    }
    loadChapters();
    return () => {
      isMounted = false;
    };
  }, [bookTitle, className, subject]);

  useEffect(() => {
    if (!chapter) return;
    let isMounted = true;
    async function loadTopics() {
      setStatus((prev) => ({ ...prev, topics: "loading" }));
      setError("");
      try {
        const data = await postJson("/topics", {
          class_name: className,
          subject,
          book_title: bookTitle,
          chapter_title: chapter
        });
        if (!isMounted) return;
        const nextTopics = data.topics || [];
        setTopics(nextTopics);
        setTopicTitle(nextTopics[0] || "");
        setSubtopics([]);
        setSubtopic("");
      } catch (err) {
        if (!isMounted) return;
        setError(err.message || "Failed to load topics");
      } finally {
        if (!isMounted) return;
        setStatus((prev) => ({ ...prev, topics: "idle" }));
      }
    }
    loadTopics();
    return () => {
      isMounted = false;
    };
  }, [chapter, className, subject, bookTitle]);

  useEffect(() => {
    if (!topicTitle) return;
    let isMounted = true;
    async function loadSubtopics() {
      setStatus((prev) => ({ ...prev, subtopics: "loading" }));
      setError("");
      try {
        const data = await postJson("/subtopics", {
          class_name: className,
          subject,
          book_title: bookTitle,
          topic_title: topicTitle,
          chapter_title: chapter
        });
        if (!isMounted) return;
        setSubtopics(data.subtopics || []);
        setSubtopic("");
      } catch (err) {
        if (!isMounted) return;
        setError(err.message || "Failed to load subtopics");
      } finally {
        if (!isMounted) return;
        setStatus((prev) => ({ ...prev, subtopics: "idle" }));
      }
    }
    loadSubtopics();
    return () => {
      isMounted = false;
    };
  }, [bookTitle, chapter, topicTitle, className, subject]);

  async function handleNotes() {
    if (!canQuery) return;
    setStatus((prev) => ({ ...prev, notes: "loading" }));
    setError("");
    try {
      const data = await postJson("/notes", {
        class_name: className,
        subject,
        book_title: bookTitle,
        topic_title: topicTitle,
        chapter_title: chapter,
        subtopic_title: subtopic
      });
      setNotes(data);
    } catch (err) {
      setError(err.message || "Failed to generate notes");
    } finally {
      setStatus((prev) => ({ ...prev, notes: "idle" }));
    }
  }

  async function handleQuestions() {
    if (!canQuery) return;
    setStatus((prev) => ({ ...prev, questions: "loading" }));
    setError("");
    try {
      const data = await postJson("/questions", {
        class_name: className,
        subject,
        book_title: bookTitle,
        topic_title: topicTitle,
        chapter_title: chapter,
        subtopic_title: subtopic
      });
      setQuestions(data);
      setMcqAnswer("");
      setShortAnswer("");
      setLongAnswer("");
      setMcqEvaluation(null);
      setShortEvaluation(null);
      setLongEvaluation(null);
    } catch (err) {
      setError(err.message || "Failed to generate questions");
    } finally {
      setStatus((prev) => ({ ...prev, questions: "idle" }));
    }
  }

  async function handleExamples() {
    if (!canQuery) return;
    setStatus((prev) => ({ ...prev, examples: "loading" }));
    setError("");
    try {
      const data = await postJson("/examples", {
        class_name: className,
        subject,
        book_title: bookTitle,
        topic_title: topicTitle,
        chapter_title: chapter,
        subtopic_title: subtopic
      });
      setExamples(data);
    } catch (err) {
      setError(err.message || "Failed to generate examples");
    } finally {
      setStatus((prev) => ({ ...prev, examples: "idle" }));
    }
  }

  async function handleEvaluation(kind) {
    if (!canQuery || !questions?.[kind]?.content) return;
    try {
      const answerMap = {
        mcq: mcqAnswer,
        short: shortAnswer,
        long: longAnswer
      };
      const statusKey = {
        mcq: "evaluationMcq",
        short: "evaluationShort",
        long: "evaluationLong"
      };
      const setterMap = {
        mcq: setMcqEvaluation,
        short: setShortEvaluation,
        long: setLongEvaluation
      };
      if (!answerMap[kind]) return;
      setStatus((prev) => ({ ...prev, [statusKey[kind]]: "loading" }));
      setError("");
      const data = await postJson("/evaluate", {
        class_name: className,
        subject,
        book_title: bookTitle,
        topic_title: topicTitle,
        chapter_title: chapter,
        subtopic_title: subtopic,
        question: questions[kind].content,
        student_answer: answerMap[kind]
      });
      setterMap[kind](data);
    } catch (err) {
      setError(err.message || "Failed to evaluate answer");
    } finally {
      setStatus((prev) => ({ ...prev, [statusKey[kind]]: "idle" }));
    }
  }

  return (
    <div className="min-h-screen px-6 py-10 md:px-12">
      <header className="animate-rise max-w-5xl">
        <p className="font-display text-sm uppercase tracking-[0.3em] text-moss">
          NCERT tutor
        </p>
        <h1 className="font-display text-4xl md:text-5xl text-ink mt-4">
          NCERT-aligned learning workspace
        </h1>
        <p className="mt-4 text-lg text-ink/80 max-w-3xl">
          Select a class, subject, chapter, and subtopic to generate notes, questions,
          worked examples, and evaluation feedback with citations.
        </p>
      </header>

      <section className="animate-rise mt-10 grid gap-6 md:grid-cols-[1.15fr_1.35fr]">
        <div className="rounded-3xl border border-clay/50 bg-white/70 p-6 shadow-sm">
          <h2 className="font-display text-2xl">Study setup</h2>
          <p className="text-sm text-ink/70 mt-2">
            Configure the chapter scope and generate learning resources.
          </p>
          {error ? (
            <div className="mt-4 rounded-xl border border-ember/40 bg-ember/10 px-4 py-3 text-sm text-ember">
              {error}
            </div>
          ) : null}
          <div className="mt-6 space-y-4">
            <div>
              <label className="text-xs uppercase tracking-[0.2em] text-ink/60">Class</label>
              <select
                className="mt-2 w-full rounded-xl border border-clay/60 bg-sand/50 px-3 py-2"
                value={className}
                onChange={(event) => setClassName(event.target.value)}
              >
                {classOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.2em] text-ink/60">Subject</label>
              <select
                className="mt-2 w-full rounded-xl border border-clay/60 bg-sand/50 px-3 py-2"
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
              >
                {subjectOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.2em] text-ink/60">Book</label>
              <select
                className="mt-2 w-full rounded-xl border border-clay/60 bg-sand/50 px-3 py-2"
                value={bookTitle}
                onChange={(event) => setBookTitle(event.target.value)}
                disabled={status.books === "loading"}
              >
                <option value="">Select book</option>
                {books.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
              {status.books === "loading" ? (
                <p className="mt-2 text-xs text-ink/60">Loading books…</p>
              ) : null}
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.2em] text-ink/60">Chapter</label>
              <select
                className="mt-2 w-full rounded-xl border border-clay/60 bg-sand/50 px-3 py-2"
                value={chapter}
                onChange={(event) => setChapter(event.target.value)}
                disabled={!bookTitle || status.chapters === "loading"}
              >
                <option value="">Select chapter</option>
                {chapters.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
              {status.chapters === "loading" ? (
                <p className="mt-2 text-xs text-ink/60">
                  Indexing the full book and loading chapters…
                </p>
              ) : null}
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.2em] text-ink/60">Topic</label>
              <select
                className="mt-2 w-full rounded-xl border border-clay/60 bg-sand/50 px-3 py-2"
                value={topicTitle}
                onChange={(event) => setTopicTitle(event.target.value)}
                disabled={!chapter || status.topics === "loading"}
              >
                <option value="">Select topic</option>
                {topics.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
              {status.topics === "loading" ? (
                <p className="mt-2 text-xs text-ink/60">Loading topics…</p>
              ) : null}
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.2em] text-ink/60">Subtopic</label>
              <select
                className="mt-2 w-full rounded-xl border border-clay/60 bg-sand/50 px-3 py-2"
                value={subtopic}
                onChange={(event) => setSubtopic(event.target.value)}
                disabled={!chapter || status.subtopics === "loading"}
              >
                <option value="">Select subtopic</option>
                {subtopics.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
              {status.subtopics === "loading" ? (
                <p className="mt-2 text-xs text-ink/60">Loading subtopics…</p>
              ) : null}
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <button
                className="rounded-xl bg-ember px-4 py-2 text-sm font-display text-white"
                type="button"
                onClick={handleNotes}
                disabled={!canQuery || status.notes === "loading"}
              >
                {status.notes === "loading" ? "Generating…" : "Notes"}
              </button>
              <button
                className="rounded-xl border border-ember/60 px-4 py-2 text-sm font-display text-ember"
                type="button"
                onClick={handleQuestions}
                disabled={!canQuery || status.questions === "loading"}
              >
                {status.questions === "loading" ? "Generating…" : "Questions"}
              </button>
              <button
                className="rounded-xl border border-moss/50 px-4 py-2 text-sm font-display text-moss"
                type="button"
                onClick={handleExamples}
                disabled={!canQuery || status.examples === "loading"}
              >
                {status.examples === "loading" ? "Generating…" : "Examples"}
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-3xl border border-clay/40 bg-ink text-sand p-6">
          <h3 className="font-display text-xl">Reference outputs</h3>
          <p className="text-sm text-sand/70 mt-2">
            Responses include citations and retrieved source excerpts.
          </p>
          <div className="mt-6 space-y-4 text-sm">
            <section className="rounded-2xl bg-sand/10 p-4">
              <h4 className="font-display text-sm text-sand/80">Notes</h4>
              <div className="mt-2 text-sand/90">
                {notes?.content ? (
                  // If notes.content is structured JSON from server, render fields
                  typeof notes.content === "object" ? (
                    <div className="space-y-4">
                      <div className="rounded-xl border border-sand/20 bg-white/5 p-3">
                        <h5 className="text-xs uppercase tracking-[0.16em] text-sand/65">Overview</h5>
                        <p className="mt-2 leading-7 text-sand/95">{notes.content.overview}</p>
                      </div>

                      <div className="rounded-xl border border-sand/20 bg-white/5 p-3">
                        <h5 className="text-xs uppercase tracking-[0.16em] text-sand/65">Key points</h5>
                        <ol className="mt-2 space-y-2 list-decimal list-inside">
                          {notes.content.key_points?.map((kp, i) => (
                            <li key={i} className="leading-6">{kp}</li>
                          ))}
                        </ol>
                      </div>

                      <div className="rounded-xl border border-sand/20 bg-white/5 p-3">
                        <h5 className="text-xs uppercase tracking-[0.16em] text-sand/65">Detailed explanation</h5>
                        <div className="mt-2 space-y-3">
                          {notes.content.detailed_paragraphs?.map((p, i) => (
                            <p key={i} className="leading-7 text-sand/95">{p}</p>
                          ))}
                        </div>
                      </div>

                      <div className="rounded-xl border border-sand/20 bg-white/5 p-3">
                        <h5 className="text-xs uppercase tracking-[0.16em] text-sand/65">Important terms</h5>
                        <ul className="mt-2 space-y-2 list-disc list-inside">
                          {notes.content.important_terms?.map((t, i) => (
                            <li key={i} className="leading-6">{t}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {notes.content.split('\n\n').map((block, i) => (
                        <p key={i} className="whitespace-pre-wrap leading-7">{block}</p>
                      ))}
                    </div>
                  )
                ) : (
                  <p className="whitespace-pre-line text-sand/90">Generate notes to see results here.</p>
                )}
              </div>
              {notes?.sources ? (
                <p className="mt-2 text-xs text-sand/70">Pages: {notes.sources}</p>
              ) : null}
            </section>

            <section className="rounded-2xl bg-sand/10 p-4">
              <h4 className="font-display text-sm text-sand/80">Questions</h4>
              <div className="mt-3 space-y-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-sand/60">MCQs</p>
                    {questions?.mcq?.content ? (
                      typeof questions.mcq.content === "object" ? (
                        questions.mcq.content.map((item, idx) => (
                          <div key={idx} className="mt-2 rounded-lg border border-sand/20 bg-white/5 p-3">
                            <div className="font-semibold">{item.question}</div>
                            <ul className="mt-2 list-disc list-inside text-sand/90">
                              {item.options?.map((opt,i)=> <li key={i}>{opt}</li>)}
                            </ul>
                            {item.answer ? <div className="mt-2 text-xs text-sand/70">Answer: {item.answer}</div> : null}
                            {item.explanation ? <div className="mt-2 text-xs text-sand/70">{item.explanation}</div> : null}
                          </div>
                        ))
                      ) : (
                        questions.mcq.content.split(/Question\s+\d+:?/).filter(Boolean).map((q, idx) => {
                          const parts = q.trim().split('\n').map(s=>s.trim()).filter(Boolean);
                          const questionLine = parts.find(p=>p.includes('?')) || '';
                          const options = parts.filter(p=>/^[A-D]\./.test(p));
                          const answerLine = parts.find(p=>/^Correct answer:/i.test(p)) || '';
                          const explanation = parts.find(p=>/^Explanation:/i.test(p)) || '';
                          return (
                            <div key={idx} className="mt-2 rounded-lg border border-sand/20 bg-white/5 p-3">
                              <div className="font-semibold">{questionLine}</div>
                              <ul className="mt-2 list-disc list-inside text-sand/90">
                                {options.map((opt,i)=> <li key={i}>{opt.replace(/^[A-D]\.\s*/, '')}</li>)}
                              </ul>
                              {answerLine ? <div className="mt-2 text-xs text-sand/70">{answerLine}</div> : null}
                              {explanation ? <div className="mt-2 text-xs text-sand/70">{explanation}</div> : null}
                            </div>
                          )
                        })
                      )
                    ) : (
                      <p className="whitespace-pre-line text-sand/90">Generate questions to see results here.</p>
                    )}
                </div>

                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-sand/60">Short / Long</p>
                  {questions?.short?.content || questions?.long?.content ? (
                    <div className="mt-2 space-y-2 text-sand/90">
                      {questions?.short?.content ? (
                        <div>
                          <p className="font-semibold">Short answer prompts</p>
                          <div className="mt-1 whitespace-pre-line">{questions.short.content}</div>
                        </div>
                      ) : null}
                      {questions?.long?.content ? (
                        <div>
                          <p className="font-semibold mt-2">Long answer prompts</p>
                          <div className="mt-1 whitespace-pre-line">{questions.long.content}</div>
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <p className="whitespace-pre-line text-sand/90">Generate questions to see results here.</p>
                  )}
                </div>

                <div className="mt-3">
                  <textarea
                    className="mt-2 w-full rounded-xl border border-sand/30 bg-sand/10 px-3 py-2 text-sm text-sand"
                    rows={3}
                    placeholder="Your MCQ answers"
                    value={mcqAnswer}
                    onChange={(event) => setMcqAnswer(event.target.value)}
                  />
                  <div className="mt-2 flex gap-2">
                    <button
                      className="rounded-xl bg-sand px-4 py-2 text-xs font-display text-ink"
                      type="button"
                      onClick={() => handleEvaluation("mcq")}
                      disabled={!canQuery || !questions?.mcq?.content || status.evaluationMcq === "loading"}
                    >
                      {status.evaluationMcq === "loading" ? "Evaluating…" : "Evaluate MCQ"}
                    </button>
                    <button
                      className="rounded-xl bg-sand px-4 py-2 text-xs font-display text-ink"
                      type="button"
                      onClick={() => handleEvaluation("short")}
                      disabled={!canQuery || !questions?.short?.content || status.evaluationShort === "loading"}
                    >
                      {status.evaluationShort === "loading" ? "Evaluating…" : "Evaluate short"}
                    </button>
                    <button
                      className="rounded-xl bg-sand px-4 py-2 text-xs font-display text-ink"
                      type="button"
                      onClick={() => handleEvaluation("long")}
                      disabled={!canQuery || !questions?.long?.content || status.evaluationLong === "loading"}
                    >
                      {status.evaluationLong === "loading" ? "Evaluating…" : "Evaluate long"}
                    </button>
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-2xl bg-sand/10 p-4">
              <h4 className="font-display text-sm text-sand/80">Solved examples</h4>
              <div className="mt-2 space-y-3 text-sand/90">
                {examples?.content ? (
                  typeof examples.content === "object" ? (
                    examples.content.map((ex, i) => (
                      <div key={i} className="rounded-lg border border-sand/20 bg-white/5 p-3">
                        <div className="font-semibold">Problem</div>
                        <p className="mt-1">{ex.problem} {ex.page?`(Page ${ex.page})`:''}</p>
                        <div className="font-semibold mt-2">Solution steps</div>
                        <ol className="list-decimal list-inside mt-1">
                          {ex.steps?.map((s, idx) => <li key={idx}>{s}</li>)}
                        </ol>
                        <div className="font-semibold mt-2">Final answer</div>
                        <p className="mt-1">{ex.final_answer}</p>
                      </div>
                    ))
                  ) : (
                    examples.content.split(/Example\s+\d+/).filter(Boolean).map((ex, i) => {
                      const parts = ex.trim().split('\n').map(s=>s.trim()).filter(Boolean);
                      return (
                        <div key={i} className="rounded-lg border border-sand/20 bg-white/5 p-3">
                          {parts.map((p, idx) => (
                            <p key={idx} className={idx===0?"font-semibold":"text-sm"}>{p}</p>
                          ))}
                        </div>
                      )
                    })
                  )
                ) : (
                  <p className="whitespace-pre-line text-sand/90">Generate examples to see results here.</p>
                )}
              </div>
              {examples?.sources ? (
                <p className="mt-2 text-xs text-sand/70">Pages: {examples.sources}</p>
              ) : null}
            </section>
          </div>
        </div>
      </section>

      <div className="fixed bottom-4 left-4 z-50 rounded-xl border border-clay/60 bg-white/85 px-3 py-2 text-xs text-ink shadow-sm backdrop-blur">
        <span className="font-display text-[11px] uppercase tracking-[0.2em] text-ink/60">
          Status
        </span>
        <div className="mt-1 text-sm text-ink/80">{statusMessage}</div>
      </div>

    </div>
  );
}
