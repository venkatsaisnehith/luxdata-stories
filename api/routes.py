"""API routes for LuxData Stories."""

import asyncio
from fastapi import APIRouter, Query
from core.database import (
    get_recent_stories,
    get_stories_by_topic,
    get_total_story_count,
    get_total_snapshot_count,
    get_topic_counts,
)
from core.scheduler import run_pipeline, get_last_run_time, is_pipeline_running

router = APIRouter()


@router.get("/api/stories")
async def list_stories(topic: str = Query(None), limit: int = Query(20, ge=1, le=100)):
    """Return recent stories, optionally filtered by topic."""
    if topic and topic.lower() != "all":
        stories = get_stories_by_topic(topic.lower(), limit=limit)
    else:
        stories = get_recent_stories(limit=limit)
    return stories


@router.get("/api/stories/topics")
async def list_topics():
    """Return available topics with story counts."""
    return get_topic_counts()


@router.get("/api/stats")
async def get_stats():
    """Return dashboard statistics."""
    return {
        "total_stories": get_total_story_count(),
        "datasets_monitored": get_total_snapshot_count(),
        "last_updated": get_last_run_time(),
        "topics_covered": len(get_topic_counts()),
    }


@router.post("/api/refresh")
async def refresh_pipeline():
    """Manually trigger the pipeline."""
    if is_pipeline_running():
        return {"status": "running", "message": "Pipeline is already running"}

    # Run pipeline in background
    asyncio.create_task(run_pipeline())
    return {"status": "running", "message": "Pipeline started"}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
