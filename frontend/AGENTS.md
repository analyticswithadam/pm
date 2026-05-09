# Frontend Codebase Architecture

This Next.js 16 (App Router) application is a statically buildable React 19 Kanban board.

## Core Dependencies
- **Next.js & React:** UI Framework and routing.
- **Tailwind CSS 4:** Styling system.
- **@dnd-kit/core & @dnd-kit/sortable:** Used to handle drag-and-drop interactions.
- **Vitest & Playwright:** Unit and E2E testing.

## Directory Structure
- `src/app/`: Next.js App Router root (`page.tsx` renders the KanbanBoard).
- `src/components/`:
  - `KanbanBoard.tsx`: Main orchestrator, holds state and `DndContext`.
  - `KanbanColumn.tsx`: Renders individual columns and handles drop zones.
  - `KanbanCard.tsx` / `KanbanCardPreview.tsx`: The draggable items.
  - `NewCardForm.tsx`: Component to add new cards.
- `src/lib/`:
  - `kanban.ts`: Core data structures (`BoardData`, `Column`, `Card`), hardcoded `initialData`, and the complex `moveCard` algorithm.

## Important Notes
- The board heavily relies on `@dnd-kit` context providers and sensors.
- State is currently localized. Future steps will sync this state with the backend via `fetch` calls.
