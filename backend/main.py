import os
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlmodel import SQLModel, Session, select
from database import engine, get_session
import models  # Important: import models so SQLModel knows about them
import schemas

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the database tables
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(title="Kanban App API", lifespan=lifespan)

# Hardcoded user for MVP
USER_USERNAME = "user"
USER_PASSWORD_HASH = "dummy_hash"

def get_or_create_user(session: Session) -> models.User:
    user = session.exec(select(models.User).where(models.User.username == USER_USERNAME)).first()
    if not user:
        user = models.User(id=str(uuid.uuid4()), username=USER_USERNAME, password_hash=USER_PASSWORD_HASH)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user

def seed_default_board(session: Session, user: models.User) -> models.Board:
    board = models.Board(id="board-1", user_id=user.id, title="Main Board")
    session.add(board)
    
    # Default columns
    col_backlog = models.Column(id="col-backlog", board_id=board.id, title="Backlog", order=0)
    col_discovery = models.Column(id="col-discovery", board_id=board.id, title="Discovery", order=1)
    col_progress = models.Column(id="col-progress", board_id=board.id, title="In Progress", order=2)
    col_review = models.Column(id="col-review", board_id=board.id, title="Review", order=3)
    col_done = models.Column(id="col-done", board_id=board.id, title="Done", order=4)
    session.add_all([col_backlog, col_discovery, col_progress, col_review, col_done])
    
    # Add a couple of initial cards
    card1 = models.Card(id="card-1", column_id="col-backlog", title="Align roadmap themes", details="Draft quarterly themes...", order=0)
    card2 = models.Card(id="card-2", column_id="col-discovery", title="Prototype analytics view", details="Sketch initial dashboard...", order=0)
    session.add_all([card1, card2])
    
    session.commit()
    session.refresh(board)
    return board

@app.get("/api/board", response_model=schemas.BoardData)
def get_board(session: Session = Depends(get_session)):
    user = get_or_create_user(session)
    board = session.exec(select(models.Board).where(models.Board.user_id == user.id)).first()
    
    if not board:
        board = seed_default_board(session, user)
        
    # Construct BoardData from DB
    columns = session.exec(select(models.Column).where(models.Column.board_id == board.id).order_by(models.Column.order)).all()
    
    board_data = schemas.BoardData(columns=[], cards={})
    
    for col in columns:
        cards = session.exec(select(models.Card).where(models.Card.column_id == col.id).order_by(models.Card.order)).all()
        card_ids = [c.id for c in cards]
        board_data.columns.append(schemas.ColumnData(id=col.id, title=col.title, cardIds=card_ids))
        for c in cards:
            board_data.cards[c.id] = schemas.CardData(id=c.id, title=c.title, details=c.details)
            
    return board_data

@app.put("/api/board")
def update_board(board_data: schemas.BoardData, session: Session = Depends(get_session)):
    user = get_or_create_user(session)
    board = session.exec(select(models.Board).where(models.Board.user_id == user.id)).first()
    
    if not board:
        board = models.Board(id="board-1", user_id=user.id, title="Main Board")
        session.add(board)
        session.commit()
        session.refresh(board)
        
    # Simplest approach: wipe all existing columns and cards for this board, and recreate them
    # This guarantees perfect synchronization with the frontend state
    existing_columns = session.exec(select(models.Column).where(models.Column.board_id == board.id)).all()
    for col in existing_columns:
        existing_cards = session.exec(select(models.Card).where(models.Card.column_id == col.id)).all()
        for card in existing_cards:
            session.delete(card)
        session.delete(col)
        
    session.commit()
    
    # Now insert everything from the incoming board_data
    for col_index, col_data in enumerate(board_data.columns):
        col = models.Column(id=col_data.id, board_id=board.id, title=col_data.title, order=col_index)
        session.add(col)
        
        for card_index, card_id in enumerate(col_data.cardIds):
            if card_id in board_data.cards:
                cdata = board_data.cards[card_id]
                card = models.Card(
                    id=cdata.id,
                    column_id=col.id,
                    title=cdata.title,
                    details=cdata.details,
                    order=card_index
                )
                session.add(card)
                
    session.commit()
    return {"status": "success"}

@app.get("/api/hello")
def hello_world():
    return {"message": "Hello World"}

# Mount the static directory to serve the frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.get("/", response_class=HTMLResponse)
    def default_home():
        return "<h1>Static folder not found. API is running.</h1>"
