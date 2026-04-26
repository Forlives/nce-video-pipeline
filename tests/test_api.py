from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.api.routes import _projects


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_projects():
    _projects.clear()
    yield
    _projects.clear()


def _generate_payload(**overrides: object) -> dict:
    base = {
        "lesson_id": 1,
        "title": "Excuse me!",
        "text": "Excuse me! Yes? Is this your handbag?",
        "level": "beginner",
        "vocabulary": ["excuse"],
        "grammar_points": ["Is this ...?"],
    }
    base.update(overrides)
    return base


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "active_projects" in data


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_pending(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/generate", json=_generate_payload())
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["lesson_id"] == 1
        assert data["title"] == "Excuse me!"
        assert "project_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_generate_validation_error(self, client: AsyncClient) -> None:
        payload = {"lesson_id": 0, "title": "", "text": ""}
        resp = await client.post("/api/v1/generate", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_invalid_style(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/generate", json=_generate_payload(style="invalid_style")
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_invalid_platform(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/generate",
            json=_generate_payload(platforms=["nonexistent"]),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_valid_platforms(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/generate",
            json=_generate_payload(platforms=["bilibili", "youtube"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["platforms"] == ["bilibili", "youtube"]

    @pytest.mark.asyncio
    async def test_generate_all_valid_styles(self, client: AsyncClient) -> None:
        for style in ("modern_dialogue", "story", "sitcom"):
            resp = await client.post(
                "/api/v1/generate", json=_generate_payload(style=style)
            )
            assert resp.status_code == 201
            assert resp.json()["style"] == style


class TestGetProject:
    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/projects/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_then_get_project(self, client: AsyncClient) -> None:
        create_resp = await client.post(
            "/api/v1/generate",
            json=_generate_payload(lesson_id=3, title="Sorry, sir.", text="My coat."),
        )
        project_id = create_resp.json()["project_id"]

        get_resp = await client.get(f"/api/v1/projects/{project_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["project_id"] == project_id
        assert data["title"] == "Sorry, sir."


class TestListProjects:
    @pytest.mark.asyncio
    async def test_list_projects_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_projects_returns_created(self, client: AsyncClient) -> None:
        await client.post("/api/v1/generate", json=_generate_payload())
        await client.post(
            "/api/v1/generate",
            json=_generate_payload(lesson_id=2, title="Pen", text="Is this your pen?"),
        )

        resp = await client.get("/api/v1/projects")
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_list_projects_filter_by_status(self, client: AsyncClient) -> None:
        from src.api.routes import ProjectRecord
        from src.models.video import VideoStatus

        _projects["direct1"] = ProjectRecord(
            project_id="direct1", lesson_id=1, title="A", status=VideoStatus.PENDING
        )
        _projects["direct2"] = ProjectRecord(
            project_id="direct2", lesson_id=2, title="B", status=VideoStatus.FAILED,
            error_message="err",
        )

        resp = await client.get("/api/v1/projects?status=pending")
        data = resp.json()
        assert data["total"] == 1
        assert all(p["status"] == "pending" for p in data["items"])

        resp2 = await client.get("/api/v1/projects?status=failed")
        data2 = resp2.json()
        assert data2["total"] == 1
        assert data2["items"][0]["project_id"] == "direct2"

    @pytest.mark.asyncio
    async def test_list_projects_pagination(self, client: AsyncClient) -> None:
        for i in range(5):
            await client.post(
                "/api/v1/generate",
                json=_generate_payload(lesson_id=i + 1, title=f"L{i+1}", text=f"Text {i+1}"),
            )

        resp = await client.get("/api/v1/projects?skip=2&limit=2")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["skip"] == 2
        assert data["limit"] == 2


class TestDeleteProject:
    @pytest.mark.asyncio
    async def test_delete_project(self, client: AsyncClient) -> None:
        create_resp = await client.post(
            "/api/v1/generate",
            json=_generate_payload(lesson_id=5, title="Nice", text="Good morning."),
        )
        project_id = create_resp.json()["project_id"]

        del_resp = await client.delete(f"/api/v1/projects/{project_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["project_id"] == project_id

        get_resp = await client.get(f"/api/v1/projects/{project_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, client: AsyncClient) -> None:
        resp = await client.delete("/api/v1/projects/nonexistent")
        assert resp.status_code == 404


class TestCancelProject:
    @pytest.mark.asyncio
    async def test_cancel_pending_project(self, client: AsyncClient) -> None:
        from src.api.routes import ProjectRecord
        from src.models.video import VideoStatus

        _projects["cancel1"] = ProjectRecord(
            project_id="cancel1", lesson_id=1, title="Cancel Me",
            status=VideoStatus.PENDING,
        )

        cancel_resp = await client.post("/api/v1/projects/cancel1/cancel")
        assert cancel_resp.status_code == 200
        data = cancel_resp.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Cancelled by user"

    @pytest.mark.asyncio
    async def test_cancel_already_failed_returns_409(self, client: AsyncClient) -> None:
        from src.api.routes import ProjectRecord
        from src.models.video import VideoStatus

        _projects["cancel2"] = ProjectRecord(
            project_id="cancel2", lesson_id=1, title="Already Failed",
            status=VideoStatus.FAILED, error_message="already broken",
        )

        resp = await client.post("/api/v1/projects/cancel2/cancel")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_cancel_published_returns_409(self, client: AsyncClient) -> None:
        from src.api.routes import ProjectRecord
        from src.models.video import VideoStatus

        _projects["cancel3"] = ProjectRecord(
            project_id="cancel3", lesson_id=1, title="Published",
            status=VideoStatus.PUBLISHED,
        )

        resp = await client.post("/api/v1/projects/cancel3/cancel")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_cancel_not_found(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/projects/nonexistent/cancel")
        assert resp.status_code == 404
