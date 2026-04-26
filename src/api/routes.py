from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from src.models.lesson import Lesson, LessonLevel
from src.models.video import VideoStatus
from src.services.publisher import Platform

router = APIRouter(prefix="/api/v1", tags=["pipeline"])
logger = logging.getLogger(__name__)

VALID_PLATFORMS = {p.value for p in Platform}
VALID_STYLES = {"modern_dialogue", "story", "sitcom"}


class ProjectRecord(BaseModel):
    """Internal storage model for a project."""

    project_id: str
    lesson_id: int
    title: str
    status: VideoStatus = VideoStatus.PENDING
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    style: str = "modern_dialogue"
    platforms: list[str] = Field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


_projects: dict[str, ProjectRecord] = {}


class GenerateRequest(BaseModel):
    lesson_id: int = Field(
        ..., ge=1, description="Lesson number (1-based)", examples=[1, 3]
    )
    title: str = Field(
        ..., min_length=1, description="Lesson title", examples=["Excuse me!"]
    )
    text: str = Field(
        ...,
        min_length=1,
        description="Original lesson text",
        examples=["Excuse me! Yes? Is this your handbag?"],
    )
    level: LessonLevel = Field(
        default=LessonLevel.BEGINNER, description="Difficulty level"
    )
    vocabulary: list[str] = Field(
        default_factory=list,
        description="Key vocabulary to highlight",
        examples=[["excuse", "handbag"]],
    )
    grammar_points: list[str] = Field(
        default_factory=list,
        description="Grammar points covered",
        examples=[["Is this your ...?"]],
    )
    style: str = Field(
        default="modern_dialogue",
        description="Adaptation style",
        examples=["modern_dialogue", "story", "sitcom"],
    )
    platforms: list[str] = Field(
        default_factory=list,
        description="Target publish platforms",
        examples=[["bilibili", "youtube"]],
    )

    @field_validator("style")
    @classmethod
    def _validate_style(cls, v: str) -> str:
        if v not in VALID_STYLES:
            raise ValueError(
                f"Invalid style '{v}'. Must be one of: {', '.join(sorted(VALID_STYLES))}"
            )
        return v

    @field_validator("platforms")
    @classmethod
    def _validate_platforms(cls, v: list[str]) -> list[str]:
        invalid = [p for p in v if p not in VALID_PLATFORMS]
        if invalid:
            raise ValueError(
                f"Unknown platforms: {invalid}. "
                f"Valid options: {', '.join(sorted(VALID_PLATFORMS))}"
            )
        return v


class ProjectResponse(BaseModel):
    project_id: str
    lesson_id: int
    title: str
    status: VideoStatus
    style: str
    platforms: list[str]
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    skip: int
    limit: int


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    active_projects: int = 0


def _record_to_response(rec: ProjectRecord) -> ProjectResponse:
    return ProjectResponse(
        project_id=rec.project_id,
        lesson_id=rec.lesson_id,
        title=rec.title,
        status=rec.status,
        style=rec.style,
        platforms=rec.platforms,
        error_message=rec.error_message,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service health status and count of active projects.",
)
async def health_check() -> HealthResponse:
    running = sum(
        1
        for p in _projects.values()
        if p.status not in (VideoStatus.FAILED, VideoStatus.PUBLISHED)
    )
    return HealthResponse(active_projects=running)


async def _run_pipeline_task(
    request: Request,
    project_id: str,
    lesson: Lesson,
    style: str,
    platform_names: list[str],
) -> None:
    """Background task that runs the full video pipeline."""
    record = _projects.get(project_id)
    if record is None:
        return

    try:
        pipeline = request.app.state.pipeline
        platforms = [Platform(name) for name in platform_names]

        project = await pipeline.run(
            lesson, style=style, platforms=platforms or None
        )

        record.status = project.status
        record.error_message = project.error_message
        record.touch()
    except Exception as exc:
        logger.error("Pipeline task failed for %s: %s", project_id, exc)
        record.status = VideoStatus.FAILED
        record.error_message = str(exc)
        record.touch()


@router.post(
    "/generate",
    response_model=ProjectResponse,
    status_code=201,
    summary="Start video generation",
    description="Creates a new project and kicks off the video generation pipeline in the background.",
)
async def generate_video(
    req: GenerateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> ProjectResponse:
    lesson = Lesson(
        lesson_id=req.lesson_id,
        title=req.title,
        text=req.text,
        level=req.level,
        vocabulary=req.vocabulary,
        grammar_points=req.grammar_points,
    )

    project_id = uuid.uuid4().hex[:12]
    record = ProjectRecord(
        project_id=project_id,
        lesson_id=lesson.lesson_id,
        title=req.title,
        style=req.style,
        platforms=req.platforms,
    )
    _projects[project_id] = record

    background_tasks.add_task(
        _run_pipeline_task, request, project_id, lesson, req.style, req.platforms
    )

    return _record_to_response(record)


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details",
    description="Retrieve the current status and metadata of a specific project.",
)
async def get_project(project_id: str) -> ProjectResponse:
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return _record_to_response(_projects[project_id])


@router.get(
    "/projects",
    response_model=ProjectListResponse,
    summary="List projects",
    description="List all projects with optional status filtering and pagination.",
)
async def list_projects(
    status: VideoStatus | None = Query(
        default=None, description="Filter by project status"
    ),
    skip: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(
        default=20, ge=1, le=100, description="Max items to return"
    ),
) -> ProjectListResponse:
    all_records = list(_projects.values())

    if status is not None:
        all_records = [r for r in all_records if r.status == status]

    total = len(all_records)
    page = all_records[skip : skip + limit]

    return ProjectListResponse(
        items=[_record_to_response(r) for r in page],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Delete a project",
    description="Remove a project from the system. Returns the deleted project data.",
)
async def delete_project(project_id: str) -> ProjectResponse:
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")
    record = _projects.pop(project_id)
    return _record_to_response(record)


@router.post(
    "/projects/{project_id}/cancel",
    response_model=ProjectResponse,
    summary="Cancel a project",
    description="Mark a running project as failed/cancelled. Only works for non-terminal states.",
)
async def cancel_project(project_id: str) -> ProjectResponse:
    if project_id not in _projects:
        raise HTTPException(status_code=404, detail="Project not found")

    record = _projects[project_id]
    terminal = {VideoStatus.FAILED, VideoStatus.PUBLISHED}
    if record.status in terminal:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel project in '{record.status.value}' state",
        )

    record.status = VideoStatus.FAILED
    record.error_message = "Cancelled by user"
    record.touch()
    return _record_to_response(record)
