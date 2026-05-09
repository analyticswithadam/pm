from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, timezone

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    boards: List["Board"] = Relationship(back_populates="user")

class Board(SQLModel, table=True):
    __tablename__ = "boards"
    id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    title: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: User = Relationship(back_populates="boards")
    columns: List["Column"] = Relationship(back_populates="board")

class Column(SQLModel, table=True):
    __tablename__ = "columns"
    id: str = Field(primary_key=True)
    board_id: str = Field(foreign_key="boards.id")
    title: str
    order: int

    board: Board = Relationship(back_populates="columns")
    cards: List["Card"] = Relationship(back_populates="column")

class Card(SQLModel, table=True):
    __tablename__ = "cards"
    id: str = Field(primary_key=True)
    column_id: str = Field(foreign_key="columns.id")
    title: str
    details: str
    order: int

    column: Column = Relationship(back_populates="cards")
