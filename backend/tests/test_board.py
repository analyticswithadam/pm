import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
import sys
import os

# Add the backend directory to sys.path so we can import properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from database import get_session
from sqlalchemy.pool import StaticPool

# Use an in-memory SQLite database for testing
sqlite_url = "sqlite:///:memory:"
engine = create_engine(
    sqlite_url, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
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

def test_get_board_seeds_default_data(client: TestClient):
    response = client.get("/api/board")
    assert response.status_code == 200
    data = response.json()
    
    assert "columns" in data
    assert "cards" in data
    assert len(data["columns"]) == 5
    assert data["columns"][0]["title"] == "Backlog"
    
    # Should have seeded 2 cards initially
    assert len(data["cards"]) == 2

def test_update_board(client: TestClient):
    # First get the seeded board
    response = client.get("/api/board")
    board_data = response.json()
    
    # Modify the board: Rename a column and add a card
    board_data["columns"][0]["title"] = "Modified Backlog"
    
    new_card_id = "test-card-999"
    board_data["cards"][new_card_id] = {
        "id": new_card_id,
        "title": "Test Title",
        "details": "Test Details"
    }
    board_data["columns"][0]["cardIds"].append(new_card_id)
    
    # Send PUT request
    put_response = client.put("/api/board", json=board_data)
    assert put_response.status_code == 200
    assert put_response.json()["status"] == "success"
    
    # Verify the changes persisted
    get_response = client.get("/api/board")
    new_board_data = get_response.json()
    
    assert new_board_data["columns"][0]["title"] == "Modified Backlog"
    assert new_card_id in new_board_data["cards"]
    assert new_board_data["cards"][new_card_id]["title"] == "Test Title"
