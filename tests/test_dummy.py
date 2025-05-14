
# tests/test_dummy.py

import sys
import os

# Agrega el directorio raíz del backend al path
sys.path.append(os.path.dirname(os.path.abspath(__file__ + "/..")))

from main import app


import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/metrics")
        assert response.status_code == 200

