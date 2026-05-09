from pydantic import BaseModel
from typing import List, Dict

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
