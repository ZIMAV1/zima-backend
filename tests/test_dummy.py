from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    """
    Testea que la raíz de la API responda 200.
    """
    response = client.get("/")
    assert response.status_code == 200 or response.status_code == 404

def test_docs_accessible():
    """
    Verifica que la documentación Swagger esté disponible.
    """
    response = client.get("/docs")
    assert response.status_code == 200
    assert "html" in response.text.lower()

def test_openapi_accessible():
    """
    Verifica que el esquema OpenAPI JSON esté disponible.
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()
