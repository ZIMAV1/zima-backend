
# tests/test_dummy.py

import sys
import os

# Agrega la raíz del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code in [200, 404]  # puede que no exista "/", pero no debe tirar error de server
