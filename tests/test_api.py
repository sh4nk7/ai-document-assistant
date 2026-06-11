"""Integration tests for the FastAPI endpoints.

Run with:
    pytest tests/test_api.py -v

These tests use a real HTTP client against a running app (via ASGI transport).
They require environment variables for database and Qdrant to be available.
Set them via docker-compose or a local .env before running.
"""

import io
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app

SAMPLE_PDF = "tests/fixtures/sample.pdf"


@pytest.fixture
def sample_pdf_bytes():
    with open(SAMPLE_PDF, "rb") as f:
        return f.read()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_upload_pdf(client, sample_pdf_bytes):
    response = await client.post(
        "/documents/upload",
        files={"file": ("sample.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] in ("ready", "processing")
    return data["id"]


@pytest.mark.asyncio
async def test_list_documents(client):
    response = await client.get("/documents/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_search(client):
    response = await client.get("/search/", params={"q": "intelligenza artificiale", "top_k": 3})
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert isinstance(body["results"], list)


@pytest.mark.asyncio
async def test_chat(client):
    response = await client.post(
        "/chat/",
        json={"question": "Di cosa tratta il documento?", "top_k": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "session_id" in body
    assert len(body["answer"]) > 0


@pytest.mark.asyncio
async def test_upload_invalid_file(client):
    response = await client.post(
        "/documents/upload",
        files={"file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_nonexistent_document(client):
    response = await client.get("/documents/nonexistent-id-12345")
    assert response.status_code == 404
