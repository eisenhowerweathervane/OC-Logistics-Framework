"""Tests for /api/documents routes."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

PRESIGN_MOCK_URL = "http://minio:9000/test-bucket/upload-url?sig=abc"


@pytest.mark.asyncio
async def test_presign_upload(client: AsyncClient):
    with patch("app.services.storage_service.presign_upload", return_value=PRESIGN_MOCK_URL):
        resp = await client.post(
            "/api/documents/presign",
            json={
                "filename": "pod.jpg",
                "mime_type": "image/jpeg",
                "target_folder": "loads/load_123/pod",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "upload_url" in data
    assert "storage_key" in data


@pytest.mark.asyncio
async def test_create_document(client: AsyncClient):
    resp = await client.post(
        "/api/documents",
        json={
            "doc_type": "pod",
            "filename": "pod.jpg",
            "mime_type": "image/jpeg",
            "storage_key": "org/loads/load_123/pod.jpg",
            "sha256": "abc123",
            "upload_source": "whatsapp",
            "doc_date": "2026-09-03",
            "nearest_city": "Chicago, IL",
            "links": [],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "pod"
    assert data["filename"] == "pod.jpg"


@pytest.mark.asyncio
async def test_create_document_with_load_link(client: AsyncClient):
    # Create a load first
    load_resp = await client.post(
        "/api/loads",
        json={
            "commodity": "Freight",
            "stops": [{"seq": 1, "stop_type": "pickup", "city": "Cleveland", "state": "OH"}],
        },
    )
    load_id = load_resp.json()["id"]

    resp = await client.post(
        "/api/documents",
        json={
            "doc_type": "bol",
            "filename": "bol.pdf",
            "mime_type": "application/pdf",
            "storage_key": f"org/loads/{load_id}/bol.pdf",
            "links": [{"entity_type": "load", "entity_id": load_id}],
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient):
    await client.post(
        "/api/documents",
        json={
            "doc_type": "pod",
            "filename": "pod.jpg",
            "mime_type": "image/jpeg",
            "storage_key": "org/docs/pod1.jpg",
            "links": [],
        },
    )
    resp = await client.get("/api/documents")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_list_documents_by_type(client: AsyncClient):
    await client.post(
        "/api/documents",
        json={
            "doc_type": "bol",
            "filename": "bol.pdf",
            "mime_type": "application/pdf",
            "storage_key": "org/docs/bol1.pdf",
            "links": [],
        },
    )
    resp = await client.get("/api/documents?doc_type=bol")
    assert resp.status_code == 200
    for doc in resp.json():
        assert doc["doc_type"] == "bol"


@pytest.mark.asyncio
async def test_download_document(client: AsyncClient):
    create = await client.post(
        "/api/documents",
        json={
            "doc_type": "pod",
            "filename": "pod.jpg",
            "mime_type": "image/jpeg",
            "storage_key": "org/docs/pod_dl.jpg",
            "links": [],
        },
    )
    doc_id = create.json()["id"]

    with patch("app.services.storage_service.presign_download", return_value="http://signed-url"):
        resp = await client.get(f"/api/documents/{doc_id}/download")
    assert resp.status_code == 200
    assert resp.json()["download_url"] == "http://signed-url"


@pytest.mark.asyncio
async def test_download_not_found(client: AsyncClient):
    import uuid

    with patch("app.services.storage_service.presign_download", return_value="http://x"):
        resp = await client.get(f"/api/documents/{uuid.uuid4()}/download")
    assert resp.status_code == 404
