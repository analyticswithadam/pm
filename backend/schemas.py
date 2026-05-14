from pydantic import BaseModel
from typing import List, Dict, Optional, Literal

class CardData(BaseModel):
    id: str
    title: str
    details: str

class ColumnData(BaseModel):
    id: str
    title: str
    cardIds: List[str]

class BoardData(BaseModel):
    columns: List[ColumnData]
    cards: Dict[str, CardData]

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]
    board: BoardData

class AICommand(BaseModel):
    action: str
    payload: Dict

class ChatResponse(BaseModel):
    reply: str
    commands: Optional[List[AICommand]] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
