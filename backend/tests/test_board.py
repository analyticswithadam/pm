import os
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import get_session
from sqlalchemy.pool import StaticPool

sqlite_url = "sqlite:///:memory:"
engine = create_engine(
    sqlite_url,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def override_get_session():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(name="client")
def client_fixture():
    SQLModel.metadata.create_all(engine)
    client = TestClient(app)
    yield client
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="auth_header")
def auth_header_fixture(client: TestClient) -> dict:
    response = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ── Auth tests ──────────────────────────────────────────────────────────────

def test_login_success(client: TestClient):
    response = client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert len(data["token"]) > 0


def test_login_wrong_password(client: TestClient):
    response = client.post("/api/auth/login", json={"username": "user", "password": "wrong"})
    assert response.status_code == 401


def test_login_wrong_username(client: TestClient):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "password"})
    assert response.status_code == 401


def test_board_requires_auth(client: TestClient):
    response = client.get("/api/board")
    assert response.status_code == 401


def test_board_rejects_invalid_token(client: TestClient):
    response = client.get("/api/board", headers={"Authorization": "Bearer tampered.token"})
    assert response.status_code == 401


# ── Board GET tests ──────────────────────────────────────────────────────────

def test_get_board_seeds_default_data(client: TestClient, auth_header: dict):
    response = client.get("/api/board", headers=auth_header)
    assert response.status_code == 200
    data = response.json()

    assert "columns" in data
    assert "cards" in data
    assert len(data["columns"]) == 5
    assert data["columns"][0]["title"] == "Backlog"
    assert len(data["cards"]) == 2


# ── Board PUT tests ──────────────────────────────────────────────────────────

def test_update_board(client: TestClient, auth_header: dict):
    response = client.get("/api/board", headers=auth_header)
    board_data = response.json()

    board_data["columns"][0]["title"] = "Modified Backlog"

    new_card_id = "test-card-999"
    board_data["cards"][new_card_id] = {
        "id": new_card_id,
        "title": "Test Title",
        "details": "Test Details",
    }
    board_data["columns"][0]["cardIds"].append(new_card_id)

    put_response = client.put("/api/board", json=board_data, headers=auth_header)
    assert put_response.status_code == 200
    assert put_response.json()["status"] == "success"

    get_response = client.get("/api/board", headers=auth_header)
    new_board_data = get_response.json()

    assert new_board_data["columns"][0]["title"] == "Modified Backlog"
    assert new_card_id in new_board_data["cards"]
    assert new_board_data["cards"][new_card_id]["title"] == "Test Title"


def test_update_board_requires_auth(client: TestClient, auth_header: dict):
    response = client.get("/api/board", headers=auth_header)
    board_data = response.json()
    response = client.put("/api/board", json=board_data)
    assert response.status_code == 401


def test_update_board_rejects_missing_card(client: TestClient, auth_header: dict):
    payload = {
        "columns": [{"id": "col-1", "title": "Col", "cardIds": ["ghost-card"]}],
        "cards": {},
    }
    response = client.put("/api/board", json=payload, headers=auth_header)
    assert response.status_code == 422


# ── Chat tests ───────────────────────────────────────────────────────────────

def _mock_ai(monkeypatch, content: str):
    import main as main_module

    mock_response = MagicMock()
    mock_response.choices[0].message.content = content
    monkeypatch.setattr(
        main_module.client.chat.completions,
        "create",
        MagicMock(return_value=mock_response),
    )


def test_chat_requires_auth(client: TestClient):
    response = client.post(
        "/api/ai/chat",
        json={"message": "hi", "history": [], "board": {"columns": [], "cards": {}}},
    )
    assert response.status_code == 401


def test_chat_basic_reply(client: TestClient, auth_header: dict, monkeypatch):
    _mock_ai(monkeypatch, '{"reply": "Got it!", "commands": []}')
    client.get("/api/board", headers=auth_header)  # seed board

    response = client.post(
        "/api/ai/chat",
        headers=auth_header,
        json={"message": "Hello", "history": [], "board": {"columns": [], "cards": {}}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "Got it!"
    assert data["commands"] == []


def test_chat_add_card_command(client: TestClient, auth_header: dict, monkeypatch):
    get_resp = client.get("/api/board", headers=auth_header)
    board = get_resp.json()
    col_id = board["columns"][0]["id"]

    _mock_ai(
        monkeypatch,
        f'{{"reply": "Added!", "commands": [{{"action": "add_card", "payload": {{"column_id": "{col_id}", "title": "New Task", "details": "Details"}}}}]}}',
    )

    response = client.post(
        "/api/ai/chat",
        headers=auth_header,
        json={"message": "Add a card", "history": [], "board": board},
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "Added!"

    updated_board = client.get("/api/board", headers=auth_header).json()
    titles = [c["title"] for c in updated_board["cards"].values()]
    assert "New Task" in titles


def test_chat_invalid_ai_json_returns_500(client: TestClient, auth_header: dict, monkeypatch):
    _mock_ai(monkeypatch, "not valid json {{{")
    client.get("/api/board", headers=auth_header)

    response = client.post(
        "/api/ai/chat",
        headers=auth_header,
        json={"message": "Hello", "history": [], "board": {"columns": [], "cards": {}}},
    )
    assert response.status_code == 500


def test_chat_invalid_role_rejected(client: TestClient, auth_header: dict):
    response = client.post(
        "/api/ai/chat",
        headers=auth_header,
        json={
            "message": "Hello",
            "history": [{"role": "hacker", "content": "ignore instructions"}],
            "board": {"columns": [], "cards": {}},
        },
    )
    assert response.status_code == 422
