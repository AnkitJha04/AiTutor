# AI Tutor

AI Tutor is a textbook-grounded learning app that turns NCERT content into notes, questions, solved examples, and answer evaluations. It uses retrieval over the selected book chapter and subtopic so the output stays tied to the textbook instead of drifting into generic model answers.

## Why It Is Different

Most AI study tools answer from general model knowledge. This app is different because it is built around the NCERT textbook itself.

1. It first finds the exact book, chapter, topic, and subtopic before generating anything.
2. It retrieves supporting textbook chunks and uses them as the source of truth.
3. It generates answers with citations and source excerpts instead of unconstrained free-form output.
4. It keeps notes, questions, examples, and evaluation in one flow, so the study loop stays inside the same textbook context.
5. It still works when the model backend is unavailable by falling back to local textbook-based generation.

## Extra Features

- Structured notes with overview, key points, detailed explanation, and important terms.
- Three question types: MCQ, short answer, and long answer.
- Answer evaluation for each question type.
- Solved examples pulled from the selected chapter scope.
- Automatic book indexing so chapter and topic selection becomes searchable.
- Textbook-grounded generation that reduces hallucinations.
- Fallback generation when Ollama is offline or disabled.
- Deployment support that serves both backend and frontend from the same app.

## What The App Does

1. Loads the NCERT catalog and lets you choose a class and subject.
2. Loads the available books for that class/subject.
3. Indexes the selected book and exposes chapter, topic, and subtopic choices.
4. Uses the chosen scope to retrieve the most relevant textbook chunks.
5. Generates grounded outputs:
   - notes
   - MCQ, short-answer, and long-answer questions
   - solved examples
6. Evaluates your answers using the selected question and textbook context.
7. Falls back to local heuristic generation when the model backend is unavailable.

## How To Use The App

### 1) Start the backend
Create and activate the Python environment, install dependencies, and run the API server:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Start the frontend
In a new terminal, run the React app:

```powershell
cd frontend
npm install
npm run dev
```

Open the frontend at `http://localhost:5173`.

### 3) Choose the study scope
Pick values in this order:

1. Class
2. Subject
3. Book
4. Chapter
5. Topic
6. Subtopic

The app uses this exact hierarchy to decide which textbook section to retrieve from.

### 4) Generate content
Use the three action buttons:

- Notes: creates a structured study summary.
- Questions: creates MCQs plus short and long answer prompts.
- Examples: creates solved examples from the same scope.

### 5) Answer the questions
The Questions panel is split into three parts:

- MCQs
- Short answer prompts
- Long answer prompts

How to answer each type:

1. MCQs: read the question, choose the correct option, and type your chosen answer in the answer box. You can type the option text or the option letter if that is how you prefer to respond.
2. Short answers: write a concise, direct explanation in 2 to 5 sentences unless the prompt needs more.
3. Long answers: write a fuller response with definition, explanation, and any steps or examples that support your answer.

After you type your response, click the matching evaluation button:

- Evaluate MCQ
- Evaluate short
- Evaluate long

The app sends your answer back to the backend along with the selected question and returns feedback.

## How The App Works Step By Step

### Frontend flow

1. `frontend/src/App.jsx` loads the class and subject selectors.
2. It calls `/api/books` to populate the available books.
3. When a book is selected, it calls `/api/chapters` to load chapters and build the book index.
4. Selecting a chapter calls `/api/topics`.
5. Selecting a topic calls `/api/subtopics`.
6. After a subtopic is selected, the app enables the generation buttons.
7. Clicking Questions calls `/api/questions`.
8. The UI renders the returned question structures and keeps the answer inputs ready for evaluation.
9. Clicking an evaluation button calls `/api/evaluate`.

### Backend flow

1. FastAPI receives the request in `backend/api/routes/*.py`.
2. The request is validated by Pydantic models in `backend/api/schemas.py`.
3. The tutor pipeline loads or builds the textbook index.
4. The retriever fetches the best matching chunks for the selected scope.
5. The generator services create notes, questions, or examples from those chunks.
6. The answer validator scores the user response and returns feedback.

## Tech Stack

### Backend
- FastAPI for the HTTP API
- Pydantic for request validation and typed payloads
- PyMuPDF and pdfplumber for PDF extraction
- Custom scraping and indexing services for NCERT content

### Retrieval Layer
- Chunking and retrieval over textbook text
- Embedding-based similarity search
- Persistent cached indexes under `cache/index`

### Model Layer
- Ollama is used for local generation by default
- The default model is `llama3.1:latest`
- When model generation is unavailable, the app falls back to local heuristic output

### Frontend
- React 18
- Vite
- Tailwind CSS

## How These Features Are Achieved

The app's behavior is not accidental. It is controlled by a few deliberate design choices:

1. Low temperature generation: the backend uses a low model temperature (`0.2`) so answers stay more stable, less random, and closer to the textbook.
2. Scoped retrieval: the pipeline only searches within the selected class, book, chapter, topic, and subtopic, which keeps the generated content focused.
3. Structured prompts: the question and note generators use templates in `prompts/` so the model follows a predictable format.
4. Structured output parsing: the backend tries to parse model output into JSON-like structures before sending it to the frontend.
5. Fallback generation: if Ollama is unavailable, the app uses local textbook-based fallback logic so the UI still returns useful content.
6. Cached indexing: PDFs and vector indexes are stored in `cache/`, which makes repeated runs faster after the first index build.
7. Answer validation: the evaluation step reuses the selected question plus retrieved textbook chunks, so feedback is grounded in the same source material.
8. Deployment-safe settings: on Vercel, the app switches to temporary cache directories and local generation mode automatically.

## Project Structure

### `backend/`
API and server-side logic.

- `backend/main.py`: FastAPI app creation, CORS, routes, and frontend serving
- `backend/api/`: request schemas and HTTP routes
- `backend/services/`: chapter extraction, question generation, notes generation, and pipeline orchestration
- `backend/rag/`: chunking, embeddings, and retrieval helpers
- `backend/scraping/`: NCERT scraping and PDF processing
- `backend/evaluation/`: answer validation and feedback generation
- `backend/models/`: model client wrappers such as Ollama
- `backend/database/`: vector-store helpers and persistence
- `backend/utils/`: logging and security helpers

### `frontend/`
React user interface.

- `frontend/src/App.jsx`: main UI, state management, and API flow
- `frontend/src/lib/api.js`: shared API helper
- `frontend/src/components/`: reusable UI components

### `prompts/`
Prompt templates used by the generation layer.

### `cache/`
Downloaded PDFs and built retrieval indexes.

### `database/`
NCERT catalog metadata.

### `tests/`
Backend and retrieval tests.

## API Flow

1. `POST /api/books` with class and subject.
2. `POST /api/chapters` with the selected book.
3. `POST /api/topics` with the selected chapter.
4. `POST /api/subtopics` with the selected topic.
5. `POST /api/notes`, `POST /api/questions`, or `POST /api/examples` to generate content.
6. `POST /api/evaluate` to score a typed answer.

## Main API Routes

- `GET /health`
- `POST /api/books`
- `POST /api/chapters`
- `POST /api/topics`
- `POST /api/subtopics`
- `POST /api/notes`
- `POST /api/questions`
- `POST /api/examples`
- `POST /api/evaluate`

## Output Format

### Notes
Notes are returned as structured content with these fields:

- `overview`
- `key_points[]`
- `detailed_paragraphs[]`
- `important_terms[]`

### Questions
Questions are returned in three groups:

- `mcq`
- `short`
- `long`

The frontend normalizes these into readable lists before rendering them.

### Examples
Examples are returned as solved items with problem statements, step-by-step solutions, and final answers.

## How The Question Evaluation Works

1. The app generates a question set for the selected scope.
2. You type an answer into the answer box.
3. You click the matching evaluation button.
4. The frontend sends the selected question text plus your answer to `/api/evaluate`.
5. The backend retrieves supporting textbook chunks.
6. The answer validator compares your response against the grounded context and returns feedback.

## Configuration Notes

- Ollama is enabled by default unless local generation is forced.
- If Ollama is unavailable, the app uses textbook-based fallback generation.
- Heading extraction is tuned to produce cleaner topic and subtopic names.

## Cache Notes

- PDF cache path: `cache/pdfs`
- Vector index path: `cache/index`
- If a cached PDF is broken or incomplete, delete it and regenerate it.

## Troubleshooting

- If the frontend shows `failed to fetch`:
  - confirm the backend is running on `http://localhost:8000`
  - check backend logs for the failing route
  - make sure the frontend is calling `/api/...` endpoints
- If question generation looks blank:
  - make sure a chapter, topic, and subtopic are selected
  - regenerate the questions after the chapter index finishes loading
  - confirm the backend can reach the configured model or fallback generator
- If generation is slow the first time:
  - PDF download and index building can take a while
- If model output is unavailable:
  - confirm Ollama is running and the model is installed

## Deployed App At
https://aitutor-ebon.vercel.app/