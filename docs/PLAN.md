# Project Plan

## Part 1: Plan
- [x] Enrich PLAN.md to detail all substeps, tests, and success criteria.
- [x] Create `frontend/AGENTS.md` to describe the existing React/Next.js codebase.
- [x] Get user sign-off on the plan.
**Tests:** N/A
**Success Criteria:** User approves the enriched plan.

## Part 2: Scaffolding
- [x] Initialize Python FastAPI backend in `backend/` utilizing `uv`.
- [x] Create basic Dockerfile and `docker-compose.yml` to run the backend.
- [x] Write `scripts/start.sh`, `scripts/start.bat`, `scripts/stop.sh`, `scripts/stop.bat`.
- [x] Create a hello world API (`/api/hello`) and serve a static dummy `index.html` at `/`.
**Tests:** Run start scripts; check `localhost:8000` and `localhost:8000/api/hello`.
**Success Criteria:** Application runs containerized, scripts work cross-platform, serving static file and simple API.

## Part 3: Add in Frontend
- [x] Update frontend `next.config.ts` to output a static export (`output: 'export'`).
- [x] Modify Docker build to build the frontend first and place the static files in the backend's static directory.
- [x] Serve the static Next.js Kanban board from the FastAPI app at `/`.
**Tests:** Build and start container; navigate to `localhost:8000` to see the React Kanban board. Run frontend unit tests (`npm run test:unit`).
**Success Criteria:** The production-built Next.js frontend is served by FastAPI inside Docker.

## Part 4: Add fake user sign in
- [x] Add a simple `/login` route in Next.js.
- [x] Protect the root `/` board layout, redirecting unauthenticated users to `/login`.
- [x] Implement hardcoded auth accepting only "user" / "password".
**Tests:** Unauthenticated user is forced to `/login`. Submitting "user"/"password" successfully grants access.
**Success Criteria:** The Kanban board is protected by the dummy sign-in barrier.

## Part 5: Database modeling
- [ ] Propose SQLite relational database schema (Users, Boards, Columns, Cards) and document in `docs/DB_SCHEMA.md`.
- [ ] Get user sign-off on the schema.
- [ ] Configure SQLite and ORM (e.g., SQLAlchemy/SQLModel) in the backend. (Note: initial testing may use a JSON payload, but persistence will be relational).
**Tests:** Startup creates `kanban.db` cleanly.
**Success Criteria:** DB schema is documented, approved, and integrated into FastAPI.

## Part 6: Backend
- [ ] Add CRUD API endpoints for Kanban (`GET /api/board`, `PUT /api/card`, etc.).
- [ ] Write comprehensive backend tests (pytest) to cover reading and modifying the database state.
**Tests:** Test API endpoints modify SQLite database accurately.
**Success Criteria:** Complete backend API allowing full manipulation of the Kanban board.

## Part 7: Frontend + Backend
- [ ] Refactor frontend (`lib/kanban.ts`, hooks) to use real data from the backend APIs instead of hardcoded `initialData`.
- [ ] Trigger API updates on card moves and edits (Drag and Drop events).
**Tests:** Move a card in UI, refresh page, verify card persists in new location.
**Success Criteria:** True full-stack persistent Kanban board.

## Part 8: AI connectivity
- [ ] Inject `OPENROUTER_API_KEY` via `.env`.
- [ ] Create `GET /api/ai/test` endpoint testing a prompt against the requested `openai/gpt-oss-120b` OpenRouter model.
**Tests:** Call `/api/ai/test` with a "2+2" prompt, expect "4" response.
**Success Criteria:** Proven backend connectivity to OpenRouter using the designated model.

## Part 9: AI with Structured Outputs
- [ ] Add `POST /api/ai/chat` taking the user message, history, and current Kanban state (serialized to JSON for the prompt).
- [ ] Configure OpenRouter to return Structured Outputs (JSON Schema) containing an AI reply and optional kanban commands (e.g., `add_card`, `move_card`).
- [ ] Translate AI outputs into backend DB operations.
**Tests:** Pass a mock "Create a card for QA" message to the endpoint, verify database receives a new card.
**Success Criteria:** AI reliably determines when and how to update the board state.

## Part 10: AI Sidebar Widget
- [ ] Build a sleek, responsive chat sidebar in the Next.js app using project colors.
- [ ] Wire the UI to send messages to `POST /api/ai/chat`.
- [ ] Trigger an automatic frontend state refresh if the AI's response indicates the board was modified.
**Tests:** Conduct end-to-end test via UI: say "move 'Design card layout' to 'Done'", verify UI updates instantly.
**Success Criteria:** A "wow" user experience blending the manual Kanban board with AI superpowers.