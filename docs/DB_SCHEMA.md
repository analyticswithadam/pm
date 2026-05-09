# Database Schema (SQLite)

This document outlines the proposed relational database schema for the Kanban Studio application, to be implemented using FastAPI and SQLModel (or SQLAlchemy).

## Tables

### 1. `users`
Supports multiple users, though the MVP will primarily rely on a single hardcoded user logic.
*   `id` (String, Primary Key) - UUID or generated ID.
*   `username` (String, Unique) - e.g., "user".
*   `password_hash` (String) - Hashed password for future-proofing, or plaintext for MVP dummy auth.
*   `created_at` (DateTime)

### 2. `boards`
Each user can have one (or multiple in the future) Kanban boards.
*   `id` (String, Primary Key)
*   `user_id` (String, Foreign Key -> `users.id`)
*   `title` (String) - e.g., "Main Board".
*   `created_at` (DateTime)

### 3. `columns`
The vertical columns on the board (e.g., "Backlog", "Discovery").
*   `id` (String, Primary Key)
*   `board_id` (String, Foreign Key -> `boards.id`)
*   `title` (String) - The name of the column.
*   `order` (Integer) - Determines the left-to-right sorting of the columns.

### 4. `cards`
The draggable task cards.
*   `id` (String, Primary Key)
*   `column_id` (String, Foreign Key -> `columns.id`)
*   `title` (String) - The main task title.
*   `details` (Text) - The descriptive details/notes.
*   `order` (Integer) - Determines the top-to-bottom sorting of cards within their specific column.

## Relationships
*   **User -> Boards:** One-to-Many
*   **Board -> Columns:** One-to-Many
*   **Column -> Cards:** One-to-Many

## Notes on IDs
The frontend currently uses string-based IDs (e.g., `card-123`). The database primary keys will be designed as strings to maintain smooth compatibility with the frontend's Drag and Drop library (`@dnd-kit`), which operates heavily on string IDs.
