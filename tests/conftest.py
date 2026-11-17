"""Configuración de pruebas.

Las variables se definen ANTES de importar la app: las pruebas usan SQLite en
memoria y un LLM simulado, así que no necesitan MySQL ni conexión a internet.
"""

import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "clave-solo-para-pruebas-" + "x" * 40
os.environ["LLM_MOCK"] = "true"

import pytest  # noqa: E402


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.database import Base, engine
    from app.main import app
    from app.services.llm_service import MockLLMService, get_llm_service

    app.dependency_overrides[get_llm_service] = lambda: MockLLMService()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_client(client):
    """Cliente con un usuario registrado y el token JWT en los headers."""
    client.post(
        "/api/auth/register",
        json={"email": "ana@correo.co", "nombre": "Ana", "password": "clave1234"},
    )
    resp = client.post(
        "/api/auth/login", data={"username": "ana@correo.co", "password": "clave1234"}
    )
    client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    return client
