import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    # Utilizing TestClient as a context manager ensures FastAPI lifespan startup/shutdown hooks execute.
    with TestClient(app) as c:
        yield c

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"

def test_get_status(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "robot_telemetry" in data
    assert data["status"] == "online"

def test_get_logs(client):
    response = client.get("/api/logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_post_command_mock(client):
    response = client.post("/api/command", json={"command": "Bring me a glass of water."})
    assert response.status_code == 200
    data = response.json()
    assert data["goal"] == "deliver_water"
    assert len(data["tasks"]) > 0

def test_post_speech_mock(client):
    # Length % 3 == 0 should return "Bring me a glass of water."
    dummy_bytes_1 = b"123"
    response_1 = client.post(
        "/api/speech",
        files={"file": ("recording.webm", dummy_bytes_1, "audio/webm")}
    )
    assert response_1.status_code == 200
    assert response_1.json()["text"] == "Bring me a glass of water."

    # Length % 3 == 1 should return "Pick up the red bottle."
    dummy_bytes_2 = b"1234"
    response_2 = client.post(
        "/api/speech",
        files={"file": ("recording.webm", dummy_bytes_2, "audio/webm")}
    )
    assert response_2.status_code == 200
    assert response_2.json()["text"] == "Pick up the red bottle."

