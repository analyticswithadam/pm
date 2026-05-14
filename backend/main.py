import os
import json
import uuid
import hmac
import hashlib
import base64
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import SQLModel, Session, select
from database import engine, get_session
import models
import schemas
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Auth configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
PASSWORD_SALT = b"kanban-app-salt"
USER_USERNAME = "user"
USER_PASSWORD_HASH = hashlib.pbkdf2_hmac("sha256", b"password", PASSWORD_SALT, 260000).hex()

security = HTTPBearer(auto_error=False)


def _verify_password(plain: str) -> bool:
    candidate = hashlib.pbkdf2_hmac("sha256", plain.encode(), PASSWORD_SALT, 260000).hex()
    return hmac.compare_digest(candidate, USER_PASSWORD_HASH)


def _create_token(username: str) -> str:
    payload = json.dumps({"sub": username, "iat": int(time.time())})
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def _decode_token(token: str) -> Optional[str]:
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        return payload.get("sub")
    except Exception:
        return None


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    username = _decode_token(credentials.credentials)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return username


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(title="Kanban App API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


def get_or_create_user(session: Session, username: str) -> models.User:
    user = session.exec(select(models.User).where(models.User.username == username)).first()
    if not user:
        user = models.User(id=str(uuid.uuid4()), username=username, password_hash=USER_PASSWORD_HASH)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def seed_default_board(session: Session, user: models.User) -> models.Board:
    board = models.Board(id=str(uuid.uuid4()), user_id=user.id, title="Main Board")
    session.add(board)

    columns = [
        models.Column(id=str(uuid.uuid4()), board_id=board.id, title="Backlog", order=0),
        models.Column(id=str(uuid.uuid4()), board_id=board.id, title="Discovery", order=1),
        models.Column(id=str(uuid.uuid4()), board_id=board.id, title="In Progress", order=2),
        models.Column(id=str(uuid.uuid4()), board_id=board.id, title="Review", order=3),
        models.Column(id=str(uuid.uuid4()), board_id=board.id, title="Done", order=4),
    ]
    session.add_all(columns)

    backlog_id = columns[0].id
    discovery_id = columns[1].id
    card1 = models.Card(
        id=str(uuid.uuid4()), column_id=backlog_id,
        title="Align roadmap themes", details="Draft quarterly themes...", order=0
    )
    card2 = models.Card(
        id=str(uuid.uuid4()), column_id=discovery_id,
        title="Prototype analytics view", details="Sketch initial dashboard...", order=0
    )
    session.add_all([card1, card2])

    session.commit()
    session.refresh(board)
    return board


@app.post("/api/auth/login", response_model=schemas.LoginResponse)
def login(request: schemas.LoginRequest):
    if request.username != USER_USERNAME or not _verify_password(request.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = _create_token(request.username)
    return schemas.LoginResponse(token=token)


@app.get("/api/board", response_model=schemas.BoardData)
def get_board(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    user = get_or_create_user(session, current_user)
    board = session.exec(select(models.Board).where(models.Board.user_id == user.id)).first()

    if not board:
        board = seed_default_board(session, user)

    columns = session.exec(
        select(models.Column).where(models.Column.board_id == board.id).order_by(models.Column.order)
    ).all()

    board_data = schemas.BoardData(columns=[], cards={})

    for col in columns:
        cards = session.exec(
            select(models.Card).where(models.Card.column_id == col.id).order_by(models.Card.order)
        ).all()
        card_ids = [c.id for c in cards]
        board_data.columns.append(schemas.ColumnData(id=col.id, title=col.title, cardIds=card_ids))
        for c in cards:
            board_data.cards[c.id] = schemas.CardData(id=c.id, title=c.title, details=c.details)

    return board_data


@app.put("/api/board")
def update_board(
    board_data: schemas.BoardData,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    # Validate that every card referenced in cardIds exists in the cards dict
    for col in board_data.columns:
        missing = [cid for cid in col.cardIds if cid not in board_data.cards]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Column '{col.id}' references unknown card IDs: {missing}",
            )

    user = get_or_create_user(session, current_user)
    board = session.exec(select(models.Board).where(models.Board.user_id == user.id)).first()

    if not board:
        board = models.Board(id=str(uuid.uuid4()), user_id=user.id, title="Main Board")
        session.add(board)
        session.commit()
        session.refresh(board)

    existing_columns = session.exec(
        select(models.Column).where(models.Column.board_id == board.id)
    ).all()
    for col in existing_columns:
        existing_cards = session.exec(
            select(models.Card).where(models.Card.column_id == col.id)
        ).all()
        for card in existing_cards:
            session.delete(card)
        session.delete(col)

    session.commit()

    for col_index, col_data in enumerate(board_data.columns):
        col = models.Column(id=col_data.id, board_id=board.id, title=col_data.title, order=col_index)
        session.add(col)

        for card_index, card_id in enumerate(col_data.cardIds):
            cdata = board_data.cards[card_id]
            card = models.Card(
                id=cdata.id,
                column_id=col.id,
                title=cdata.title,
                details=cdata.details,
                order=card_index,
            )
            session.add(card)

    session.commit()
    return {"status": "success"}


@app.get("/api/hello")
def hello_world():
    return {"message": "Hello World"}


@app.get("/api/ai/test")
def test_ai():
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": "What is 2+2? Answer with just the number."}],
        )
        answer = response.choices[0].message.content.strip()
        return {"status": "success", "answer": answer}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/ai/chat", response_model=schemas.ChatResponse)
def chat_with_ai(
    request: schemas.ChatRequest,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
):
    user = get_or_create_user(session, current_user)
    session.exec(select(models.Board).where(models.Board.user_id == user.id)).first()

    system_prompt = f"""
    You are a project management assistant. You help the user manage their Kanban board.
    The current board state is: {request.board.model_dump_json()}

    You must respond in JSON format with a 'reply' (string) and an optional 'commands' (array of objects).
    Each command object must have an 'action' and a 'payload'.

    Supported actions:
    - add_card: payload = {{"column_id": str, "title": str, "details": str}}
    - move_card: payload = {{"card_id": str, "column_id": str}}
    - delete_card: payload = {{"card_id": str}}
    - rename_column: payload = {{"column_id": str, "title": str}}

    Example:
    {{
        "reply": "I've added a new card to the Backlog for you.",
        "commands": [
            {{"action": "add_card", "payload": {{"column_id": "col-backlog", "title": "New Task", "details": "Description"}} }}
        ]
    }}
    """

    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            response_format={"type": "json_object"},
        )

        try:
            ai_data = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            logger.error("AI returned non-JSON response")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI returned an unreadable response. Please try again.",
            )

        reply = ai_data.get("reply", "")
        commands = ai_data.get("commands", [])

        for cmd in commands:
            action = cmd.get("action")
            payload = cmd.get("payload", {})

            if action == "add_card":
                col_id = payload.get("column_id")
                cards = session.exec(
                    select(models.Card).where(models.Card.column_id == col_id)
                ).all()
                max_order = max((c.order for c in cards), default=-1)
                new_card = models.Card(
                    id=f"card-{uuid.uuid4().hex[:8]}",
                    column_id=col_id,
                    title=payload.get("title", "Untitled"),
                    details=payload.get("details", ""),
                    order=max_order + 1,
                )
                session.add(new_card)

            elif action == "move_card":
                card_id = payload.get("card_id")
                new_col_id = payload.get("column_id")
                card = session.get(models.Card, card_id)
                if card:
                    # Query destination before reassigning column_id to avoid counting this card twice
                    dest_cards = session.exec(
                        select(models.Card).where(models.Card.column_id == new_col_id)
                    ).all()
                    max_order = max(
                        (c.order for c in dest_cards if c.id != card_id), default=-1
                    )
                    card.column_id = new_col_id
                    card.order = max_order + 1

            elif action == "delete_card":
                card_id = payload.get("card_id")
                card = session.get(models.Card, card_id)
                if card:
                    session.delete(card)

            elif action == "rename_column":
                col_id = payload.get("column_id")
                new_title = payload.get("title")
                column = session.get(models.Column, col_id)
                if column:
                    column.title = new_title

        session.commit()
        return schemas.ChatResponse(reply=reply, commands=commands)

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error in chat endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


# Mount the static directory to serve the frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.get("/", response_class=HTMLResponse)
    def default_home():
        return "<h1>Static folder not found. API is running.</h1>"
