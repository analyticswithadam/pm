# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack Kanban board app with AI chat integration. FastAPI (Python) serves both the REST API and the statically-exported Next.js frontend as a single Docker container. AI features use OpenRouter (`openai/gpt-oss-120b`).

## Running the App

```bash
# Start (builds and runs Docker container)
./scripts/start.sh       # Mac/Linux
scripts\start.bat        # Windows

# Stop
./scripts/stop.sh
```

The app runs at `http://localhost:8000`. Login: `user` / `password`.

## Backend

```bash
cd backend

# Install dependencies (uses uv inside Docker; locally you can use uv or pip)
uv sync

# Run tests
uv run pytest

# Run a single test file
uv run pytest tests/test_api.py

# Run dev server locally (not containerized)
uv run uvicorn main:app --reload
```

Key files:
- `main.py` — all API routes and business logic
- `models.py` — SQLModel ORM models (User, Board, Column, Card)
- `schemas.py` — Pydantic request/response schemas (BoardData, ChatRequest, ChatResponse)
- `database.py` — SQLite engine and session factory

## Frontend

```bash
cd frontend

npm install
npm run dev           # Dev server (proxies /api to localhost:8000 in dev)
npm run build         # Static export to out/
npm run lint          # ESLint

npm run test:unit     # Vitest unit tests
npm run test:e2e      # Playwright E2E tests
npm run test:all      # Both
```

Key files:
- `src/hooks/useKanbanData.ts` — fetches board from `/api/board`, exposes `syncBoard()` (PUT) and `fetchBoard()` (GET)
- `src/lib/kanban.ts` — `BoardData`/`Column`/`Card` types, `moveCard` algorithm
- `src/components/KanbanBoard.tsx` — top-level state holder and `DndContext`
- `src/components/ChatSidebar.tsx` — AI chat widget, calls `POST /api/ai/chat`, triggers `fetchBoard()` when board is modified

## Architecture

### Data Flow

The frontend uses a **bulk sync** strategy: every user action (drag-drop, rename, add, delete) calls `syncBoard(newBoard)`, which PUTs the entire board state to `/api/board`. The backend wipes and recreates all columns and cards on each PUT.

AI chat (`POST /api/ai/chat`) receives the full board state + message history, returns a `reply` string plus optional `commands` (`add_card`, `move_card`, `delete_card`, `rename_column`). The backend applies commands directly to the DB; the frontend then re-fetches the board if `commands` is non-empty.

### Board State Shape

Both frontend and backend share this structure:
```
BoardData {
  columns: [{ id, title, cardIds: [...] }]  // ordered
  cards:   { [cardId]: { id, title, details } }
}
```

### Docker Build

The Dockerfile builds the Next.js frontend first (`npm run build`), copies `frontend/out/` into `backend/static/`, then runs the FastAPI app. FastAPI mounts `backend/static/` at `/` after all API routes are registered — order matters.

## Environment

`.env` in the project root (loaded by both Docker and local backend via `python-dotenv`):
```
OPENROUTER_API_KEY=...
```

## Coding Standards

- No over-engineering; simplicity first
- No emojis, ever
- Identify root cause before fixing — prove with evidence
- Keep READMEs minimal
