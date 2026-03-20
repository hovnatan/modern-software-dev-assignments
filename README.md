# Assignments for CS146S: The Modern Software Developer

Home of the assignments for [CS146S: The Modern Software Developer](https://themodernsoftware.dev), taught at Stanford University (fall 2025).

This repository contains multiple weekly exercises. The **root `pyproject.toml`** defines dependencies for the **Week 2 Action Item Extractor**—a small [FastAPI](https://fastapi.tiangolo.com/) service with SQLite persistence, a static HTML frontend, heuristic and LLM-based extraction of tasks from notes, and automated tests.

---

## Week 2 application overview

The Week 2 app helps you turn free-form notes into **action items** stored in a database:

- **Heuristic extraction** (`/action-items/extract`) uses line patterns (bullets, `todo:`, checkboxes, etc.) and light sentence heuristics.
- **LLM extraction** (`/action-items/extract-llm`) uses [Ollama](https://ollama.com/) with JSON-schema–constrained output when a local model is available.
- **Notes** can be created via the API or saved automatically when extracting with `save_note: true`.
- The **frontend** at `/` offers *Extract*, *Extract LLM*, and *List Notes* against these APIs.

SQLite lives under `week2/data/app.db` (created on startup).

---

## Setup and run

Requires **Python 3.10+**. From the **repository root**:

### Option A: Poetry

1. Install [Anaconda](https://www.anaconda.com/download) (or another Python 3.10+ environment), then create and activate an environment, e.g.:

   ```bash
   conda create -n cs146s python=3.12 -y
   conda activate cs146s
   ```

2. Install [Poetry](https://python-poetry.org/docs/#installation) if needed.

3. Install dependencies:

   ```bash
   poetry install --no-interaction
   ```

4. Run the API (serves the Week 2 UI at [http://127.0.0.1:8000/](http://127.0.0.1:8000/)):

   ```bash
   poetry run uvicorn week2.app.main:app --reload
   ```

### Option B: uv

```bash
uv sync --group dev
uv run uvicorn week2.app.main:app --reload
```

### Optional: LLM extraction (Ollama)

For `POST /action-items/extract-llm` to succeed:

1. Run a local [Ollama](https://ollama.com/) server (default `http://localhost:11434`).
2. Pull a model that supports structured outputs, e.g.:

   ```bash
   ollama pull llama3.1:8b
   ```

3. Optionally set `OLLAMA_MODEL` (default in code: `llama3.1:8b`).

If Ollama is unreachable or the response cannot be parsed, the API responds with **503** and a JSON `detail` message.

---

## API endpoints and behavior

Base URL (local): `http://127.0.0.1:8000`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the Week 2 HTML UI (`week2/frontend/index.html`). |
| `GET` | `/static/...` | Static files from `week2/frontend/`. |
| `POST` | `/notes` | Create a note. Body: `{ "content": "..." }`. Returns `NoteRead` (201). |
| `GET` | `/notes` | List all notes, newest first. Returns `NoteRead[]`. |
| `GET` | `/notes/{note_id}` | Get one note by id. **404** if missing. |
| `POST` | `/action-items/extract` | Extract action items with **heuristics**. Body: `{ "text": "...", "save_note": false }`. Optionally saves the full text as a note and links new items. Returns `note_id` (or `null`) and `items` with database ids. |
| `POST` | `/action-items/extract-llm` | Same contract as `/extract`, but uses **Ollama**. **503** on LLM/unparseable errors. |
| `GET` | `/action-items` | List action items. Query: optional `note_id` to filter by linked note. |
| `POST` | `/action-items/{action_item_id}/done` | Set done flag. Body: `{ "done": true }` (default). **404** if id missing. |

**Schemas (summary)**

- **NoteRead**: `id`, `content`, `created_at`
- **ExtractRequest**: `text` (required), `save_note` (boolean, default `false`)
- **ExtractResponse**: `note_id` (`int` or `null`), `items`: `[{ "id", "text" }, ...]`
- **ActionItemRead**: `id`, `note_id`, `text`, `done`, `created_at`

OpenAPI / Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (when the server is running).

---

## Running the test suite

From the repository root, with dev dependencies installed:

```bash
# All Week 2 tests (mocked LLM; no Ollama required for default extract tests)
pytest week2/tests/ -v
```

**Heuristic + mocked LLM unit tests** (fast, CI-friendly):

```bash
pytest week2/tests/test_extract.py -q
```

**Live Ollama integration tests** (`pytest` marker `ollama`): they call a real local Ollama instance and are **skipped** if the server or model is unavailable.

```bash
pytest week2/tests/test_extract_ollama_live.py -v
```

To run Week 2 tests **excluding** Ollama-marked tests:

```bash
pytest week2/tests/ -m "not ollama"
```

---

## Other weeks

Additional assignments may live under `week4/`, `week5/`, etc., with their own `README.md` or `Makefile` where applicable. The root Python project and this document focus on the **Week 2** FastAPI application described above.
