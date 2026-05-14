# Code Review: Kanban Board Application

**Date:** 2026-05-14  
**Reviewer:** Claude Code  
**Scope:** Full stack — `backend/` (FastAPI/SQLite) and `frontend/` (Next.js/TypeScript)  
**Commit:** `52929e2`

---

## Summary

The codebase is a clean, readable MVP with a clear architecture. The main concerns fall into four buckets: security posture (fake auth, no server-side session validation, SQL logging on), silent failure paths (sync errors swallowed, chat errors return HTTP 200), performance (unbounded PUT-on-every-drag-event during drag), and test coverage (2 happy-path tests; no error cases, no chat endpoint tests). None of these require large structural changes to fix.

---

## Severity Legend

| Level | Meaning |
|---|---|
| **Critical** | Data loss, security breach, or broken functionality |
| **High** | Significant user-facing bug or meaningful security weakness |
| **Medium** | Code quality, subtle bug, or missing safeguard |
| **Low** | Cleanup, style, or minor improvement |

---

## Security

### [Critical] Authentication is entirely client-side

**Files:** `frontend/src/app/login/page.tsx`, `frontend/src/components/AuthProvider.tsx`

The login check compares credentials against hardcoded strings in the browser and stores `"true"` in `localStorage`. No token is issued; no server verifies identity on any subsequent request. Any user can open DevTools and run `localStorage.setItem("auth", "true")` to gain access. All API endpoints are publicly reachable without credentials.

**Action:** Issue a signed session token (JWT or opaque) on login, validate it server-side on every API request via a FastAPI dependency. Store it in an HTTP-only cookie.

---

### [High] `USER_PASSWORD_HASH` is never used for verification

**File:** `backend/main.py:32`

```python
USER_PASSWORD_HASH = "dummy_hash"
```

The field exists in the model and is stored in the database, but no code ever compares a submitted password against it. The login endpoint does not exist in the backend at all — the frontend never calls one.

**Action:** Implement a `POST /api/auth/login` endpoint. Hash the password with `bcrypt` and verify on login.

---

### [High] SQL query logging enabled (`echo=True`)

**File:** `backend/database.py:7`

```python
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)
```

Every SQL statement, including full board and card data, is printed to stdout. In a containerized deployment this goes to the container log, which may be captured by log aggregators, visible to ops staff, or accidentally included in debug dumps.

**Action:** Set `echo=False` (or `echo=os.getenv("SQL_ECHO", "false") == "true"`) and use Python's `logging` module for structured application logs.

---

### [Medium] No CORS policy configured

**File:** `backend/main.py`

FastAPI's default behaviour with no CORS middleware is to allow all origins in some configurations, or to reject cross-origin requests with no clear signal, depending on the client. For a deployed app serving the frontend from the same origin this is acceptable, but there is no explicit policy.

**Action:** Add `CORSMiddleware` with an explicit `allow_origins` list, even if that list is just `["http://localhost:3000"]` for development.

---

### [Medium] No request size limits

**File:** `backend/main.py`

The `PUT /api/board` endpoint accepts an unbounded JSON body. A malicious or buggy client could POST megabytes of card data, consuming memory and CPU.

**Action:** Add a `Content-Length` check or FastAPI middleware to cap request body size.

---

### [Low] `.env` is gitignored but present on disk

The `.gitignore` correctly excludes `.env`, so the API key is not committed. No action needed, but worth noting that the file should not be shared, copied into Docker images, or committed in CI pipeline configs.

---

## Bugs and Logic Errors

### [Critical] Sync errors are silently swallowed with no rollback

**File:** `frontend/src/hooks/useKanbanData.ts:29-45`

```typescript
const syncBoard = async (newBoard: BoardData) => {
  setBoard(newBoard);          // optimistic update applied immediately
  try {
    const res = await fetch("/api/board", { method: "PUT", ... });
    if (!res.ok) throw new Error("Failed to sync board data");
  } catch (err: any) {
    console.error("Sync error:", err);   // error silently logged only
  }
};
```

If the PUT fails (network error, server error, timeout), the UI shows the new state while the database still has the old state. The user has no idea their change was lost, and the next page load will revert their work.

**Action:** Save `previousBoard` before the optimistic update. In the catch block, call `setBoard(previousBoard)` to roll back and surface an error message to the user (toast, banner, or inline).

---

### [High] `handleDragOver` fires a PUT request on every drag-over event

**File:** `frontend/src/components/KanbanBoard.tsx:44-58`

```typescript
const handleDragOver = (event: DragOverEvent) => {
  ...
  syncBoard({          // PUT /api/board on every pixel of movement over a new column
    ...board,
    columns: moveCard(board.columns, active.id as string, over.id as string),
  });
};
```

`onDragOver` fires many times per second while the user drags. Each call triggers a full `PUT /api/board`. A three-second drag across two columns can produce dozens of network requests and database wipe-recreate cycles.

**Action:** Handle cross-column reordering optimistically in local state during drag (`setBoard` only, no `syncBoard`). Call `syncBoard` once in `handleDragEnd` with the final state.

---

### [High] Chat API errors return HTTP 200 with an error string

**File:** `backend/main.py:238-239`

```python
except Exception as e:
    return schemas.ChatResponse(reply=f"Sorry, I encountered an error: {str(e)}")
```

The client receives a 200 response whose `reply` field happens to contain an error message. The exception detail (which may include API keys, stack traces, or internal paths in `str(e)`) is sent to the browser. The client has no way to distinguish a genuine reply from a failure without parsing the string.

**Action:** Log the exception server-side. Return an appropriate HTTP error status (500 or 503) so the client can handle it distinctly. Do not expose `str(e)` to the client.

---

### [High] Chat response `data.reply` accessed without checking `response.ok`

**File:** `frontend/src/components/ChatSidebar.tsx:52-54`

```typescript
const data = await response.json();
setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
```

If the server returns a non-2xx status (e.g., 500, 429), `data.reply` will be `undefined` and the message shown to the user will be the string `"undefined"`.

**Action:** Check `response.ok` before accessing `data.reply`. Fall through to the catch block or show a distinct error message on non-2xx.

---

### [Medium] `move_card` order calculation includes the card being moved

**File:** `backend/main.py:217-219`

```python
elif action == "move_card":
    card = session.get(models.Card, card_id)
    if card:
        card.column_id = new_col_id
        cards = session.exec(select(models.Card).where(models.Card.column_id == new_col_id)).all()
        max_order = max([c.order for c in cards], default=-1)
        card.order = max_order + 1
```

If `new_col_id` equals `card.column_id` (the card is already there), or if the session cache includes the card before it is moved, the query returns the card itself as part of `cards`, inflating `max_order`. The card ends up placed after itself.

**Action:** Fetch the destination column's cards before reassigning `card.column_id`, or filter out the card being moved from the result.

---

### [Medium] `import json` inside a function body

**File:** `backend/main.py:185`

```python
import json
ai_data = json.loads(response.choices[0].message.content)
```

This is a standard library module; importing inside a function is unconventional and makes dependencies harder to scan. Python caches imports after the first call, so there is no correctness issue, only a code quality one.

**Action:** Move `import json` to the top of `main.py` with the other imports.

---

### [Medium] AI JSON response parsed without a try/except

**File:** `backend/main.py:186`

```python
ai_data = json.loads(response.choices[0].message.content)
```

If the model returns malformed JSON (possible with some models even when `response_format={"type": "json_object"}` is set), this raises `json.JSONDecodeError` which is caught by the outer `except Exception`, leaking the raw model output in the error message.

**Action:** Wrap the JSON parse in its own `try/except json.JSONDecodeError` with a specific log message and a clean user-facing reply.

---

### [Low] Cards referenced in `cardIds` but missing from `cards` dict are silently skipped

**File:** `backend/main.py:113-114`

```python
for card_index, card_id in enumerate(col_data.cardIds):
    if card_id in board_data.cards:
```

A mismatched board state (e.g., a frontend bug) causes cards to disappear without any error. The response still returns 200.

**Action:** Return a 422 Unprocessable Entity if any `cardId` is not present in `board_data.cards`, so the client knows the payload was inconsistent.

---

## Performance

### [High] Full board wipe-and-recreate on every PUT

**File:** `backend/main.py:97-125`

Every `PUT /api/board` deletes every column and card for the board, then inserts them all from scratch. For a 50-card board with 5 columns, every drag-drop generates 56 DELETEs and 56 INSERTs. Combined with the `handleDragOver` issue above, a single drag gesture can trigger thousands of database operations.

**Action:** (Complementary to the `handleDragOver` fix above.) Consider diffing the incoming board against the existing state and issuing targeted UPDATE statements for changed rows. At minimum, fix the drag-over issue to reduce the call frequency to once-per-drop.

---

### [Medium] N+1 query pattern on board fetch

**File:** `backend/main.py:73-82`

```python
columns = session.exec(select(models.Column)...).all()   # 1 query
for col in columns:
    cards = session.exec(select(models.Card)...).all()   # N queries
```

For 5 columns this is 6 queries. For larger boards it scales linearly.

**Action:** Fetch all cards for the board in a single query (`WHERE column_id IN (...)`) and group them in Python, or use SQLModel's `selectinload` to eager-load relationships.

---

### [Medium] Full board state sent on every chat message

**File:** `frontend/src/components/ChatSidebar.tsx:45-49`

```typescript
body: JSON.stringify({
  message: userMessage,
  history: messages,   // grows with every exchange
  board: board,        // entire board on every message
}),
```

Both the full message history and the full board state grow over the session. For a long conversation with a large board, individual requests become large, increasing latency and cost.

**Action:** Truncate history to the last N messages (e.g., last 10). Consider omitting card `details` from the board snapshot sent to the AI unless the user's message explicitly asks about them.

---

### [Low] Chat message list grows without bound

**File:** `frontend/src/components/ChatSidebar.tsx:20`

`messages` is an unbounded in-memory array. Very long sessions accumulate many items, causing the DOM to grow and re-renders to slow down.

**Action:** Cap the rendered message list at a reasonable limit (e.g., 100 messages) with a "load earlier" affordance, or simply trim the oldest messages.

---

## Code Quality

### [Medium] `AICommand.payload` is an untyped `Dict`

**File:** `backend/schemas.py:29`

```python
class AICommand(BaseModel):
    action: str
    payload: Dict
```

`Dict` with no type parameters accepts any structure. A `Literal` union on `action` and per-action payload schemas would catch malformed AI responses at the Pydantic layer instead of failing silently at runtime.

**Action:** Define `AddCardPayload`, `MoveCardPayload`, `DeleteCardPayload`, `RenameColumnPayload` schemas and use a `Union` discriminated by `action`.

---

### [Medium] `ChatMessage.role` is an unvalidated `str`

**File:** `backend/schemas.py:18-20`

```python
class ChatMessage(BaseModel):
    role: str
    content: str
```

Any string is accepted as `role`. The OpenAI client will raise an error at call time if an invalid role is passed.

**Action:** Use `Literal["user", "assistant", "system"]` for `role`.

---

### [Medium] Hardcoded board and column IDs in seed data

**File:** `backend/main.py:44, 48-52, 56-57`

```python
board = models.Board(id="board-1", ...)
col_backlog = models.Column(id="col-backlog", ...)
card1 = models.Card(id="card-1", ...)
```

Hardcoded IDs prevent adding multi-user or multi-board support without a schema change. They also couple the AI prompt's column ID references to magic strings.

**Action:** Generate IDs with `uuid.uuid4()` at seed time (consistent with how new cards are created on line 202).

---

### [Medium] `catch (err: any)` used in two places

**Files:** `frontend/src/hooks/useKanbanData.ts:18, 43`

Using `any` defeats TypeScript's error typing. `unknown` is safer and forces an explicit type check before accessing properties.

**Action:** Replace `err: any` with `err: unknown` and narrow the type (`err instanceof Error`) before accessing `.message`.

---

### [Low] `handleSignOut` has no confirmation

**File:** `frontend/src/components/KanbanBoard.tsx:27-30`

A misclick on "Sign Out" navigates away immediately. For a board that has unsaved pending syncs this could abandon in-flight requests.

**Action:** Either add a brief confirmation dialog or disable the button while a sync is in flight.

---

### [Low] Unused `X` import in `ChatSidebar.tsx`

**File:** `frontend/src/components/ChatSidebar.tsx:5`

```typescript
import { Send, Bot, User, X, Sparkles, MessageSquare } from "lucide-react";
```

`X` and `MessageSquare` are imported but not used in the rendered output (the sidebar open/close toggle was apparently removed).

**Action:** Remove unused imports.

---

## Test Coverage

### [High] Only two tests, both happy path

**File:** `backend/tests/test_board.py`

The test suite covers `GET /api/board` (seeding) and `PUT /api/board` (basic update). Missing:

- `PUT /api/board` with a `cardId` not present in `cards` (should return 422)
- `PUT /api/board` with an empty `columns` list
- `POST /api/ai/chat` — no tests at all for this endpoint
- Each AI command type (`add_card`, `move_card`, `delete_card`, `rename_column`)
- AI returning malformed JSON
- Board not found on chat request
- `GET /api/board` response shape validation

**Action:** Add a test for each of the above. The existing test harness (in-memory SQLite, `TestClient`) is correct and easy to extend.

---

### [Medium] Frontend tests do not cover sync failure

**File:** `frontend/src/components/KanbanBoard.test.tsx`

The frontend test mocks `fetch` to succeed. There is no test that exercises the error path in `syncBoard` (what happens when the PUT returns 500).

**Action:** Add a test that mocks `fetch` to reject and asserts that the board state is rolled back (once rollback is implemented) and an error is shown.

---

## Architecture Notes

These are observations rather than action items; they reflect the intentional simplicity of an MVP.

- **Single-user, single-board design** — the `get_or_create_user` pattern and hardcoded `board-1` ID mean the app cannot support multiple users without schema and logic changes. This is fine for an MVP but worth documenting as a known constraint.
- **No API versioning** — all routes are under `/api/`. Adding `/api/v1/` now costs nothing and avoids breaking clients when the contract changes.
- **No structured logging** — `print`-based debugging (via `echo=True`) is the only observability. Adding Python `logging` with a log level env var would make production debugging much easier.
- **No rate limiting on the AI endpoint** — a chatty frontend (or a browser tab left open) could exhaust OpenRouter credits. A simple per-IP rate limiter (e.g., `slowapi`) would provide a backstop.

---

## Prioritised Action List

| Priority | Action | File(s) |
|---|---|---|
| 1 | Implement real server-side auth (JWT + HTTP-only cookie) | `backend/main.py`, `frontend/` |
| 2 | Roll back board state and show error on sync failure | `frontend/src/hooks/useKanbanData.ts` |
| 3 | Call `syncBoard` only in `handleDragEnd`, not `handleDragOver` | `frontend/src/components/KanbanBoard.tsx` |
| 4 | Set `echo=False` in database engine | `backend/database.py` |
| 5 | Fix chat API error handling (return 500, don't expose `str(e)`) | `backend/main.py` |
| 6 | Check `response.ok` before accessing `data.reply` in ChatSidebar | `frontend/src/components/ChatSidebar.tsx` |
| 7 | Add tests for chat endpoint and error cases | `backend/tests/test_board.py` |
| 8 | Move `import json` to top of file | `backend/main.py` |
| 9 | Add CORS middleware with explicit origin list | `backend/main.py` |
| 10 | Type `AICommand.payload` and `ChatMessage.role` properly | `backend/schemas.py` |
