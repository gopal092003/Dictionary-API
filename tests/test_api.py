from fastapi.testclient import TestClient
from app.main import create_app

app = create_app()
client = TestClient(app)

def test_home():
    response = client.get("/")
    assert response.status_code == 200

def test_define_word():
    response = client.get("/define/apple")
    assert response.status_code == 200

def test_invalid_word():
    response = client.get("/define/asdkfjhasdkjfh")
    assert response.status_code == 404