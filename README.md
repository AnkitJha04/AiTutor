# AI Tutor

A textbook-grounded AI tutor built with FastAPI + React. The app generates notes, questions, and solved examples from NCERT book content and includes citations.

## What It Does
- Downloads and caches NCERT books (including ZIP chapter bundles merged into one PDF)
- Extracts chapter/topic/subtopic structure from the textbook
- Builds retrieval context from the selected scope
- Generates:
   - structured notes
   - MCQ, short-answer, and long-answer questions
   - solved examples
- Evaluates student answers with rubric-style feedback
- Falls back to textbook-only generation if model generation is unavailable

## Tech Stack
- Backend: FastAPI, Pydantic, httpx, PyMuPDF, pdfplumber
- Retrieval: chunking + embeddings + FAISS index
- Model: Ollama (`llama3.1:latest` by default)
- Frontend: React (Vite) + Tailwind CSS

## Project Structure
- `backend/` API routes, services, retrieval, model client, scraping
- `frontend/` React UI
- `prompts/` grounded generation prompts
- `cache/` downloaded PDFs and built indexes
- `database/` NCERT catalog JSON
- `tests/` backend test suite

## Quick Start

### 1) Backend setup
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Run backend
```powershell
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 3) Run frontend
```powershell
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:5173`

## API Flow (Hierarchy)
1. `POST /api/books` with class + subject
2. `POST /api/chapters` with selected book
3. `POST /api/topics` with selected chapter
4. `POST /api/subtopics` with selected topic
5. `POST /api/notes`, `POST /api/questions`, or `POST /api/examples`
6. `POST /api/evaluate` for answer feedback

## Main API Routes
- `GET /health`
- `GET /api/books` (catalog-style list)
- `POST /api/books` (filtered by class + subject)
- `POST /api/chapters`
- `POST /api/topics`
- `POST /api/subtopics`
- `POST /api/notes`
- `POST /api/questions`
- `POST /api/examples`
- `POST /api/evaluate`

## Generation Output Format
- Notes return structured content:
   - `overview`
   - `key_points[]`
   - `detailed_paragraphs[]`
   - `important_terms[]`
- Questions return:
   - `mcq`
   - `short`
   - `long`
- Examples return structured solved items with steps

## Configuration Notes
- Ollama is enabled by default (`force_local_generation=False`)
- If Ollama is unavailable, textbook fallback generators are used
- Heading extraction is tuned for cleaner topic/subtopic names

## Cache Notes
- PDF cache path: `cache/pdfs`
- Vector index path: `cache/index`
- If a cached PDF is broken/incomplete, delete it and regenerate

## Troubleshooting
- If frontend shows "failed to fetch":
   - ensure backend is running on `http://localhost:8000`
   - check backend logs for request errors
   - verify frontend calls `/api/...` endpoints and correct payload fields
- If generation is slow the first time:
   - PDF download + indexing may take time
- If model output is unavailable:
   - confirm Ollama is running and model is installed
