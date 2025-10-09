"""Github endpoints.

These endpoints orchestrate data refreshes from GitHub and creation of snapshots.
They are intentionally thin: HTTP concerns only, delegating business logic to
the `application` layer.
"""

from fastapi import APIRouter, Query
from sqlalchemy.orm import Session

from src.application.refresh import refresh_issues, refresh_pull_requests
from src.application.snapshot import create_snapshot_from_project
from src.services.db import SessionLocal

router = APIRouter(tags=["github"])


@router.post(
    "/refresh",
    summary="Refresh Issues and PRs (no Project Status sync)",
    response_model=None,
)
def refresh_ingest() -> None:
    """Fetch latest GitHub Issues and PRs and persist them.

    Notes
    -----
    - This does *not* sync Project (v2) Status → `Task.column_name`.
    - Use `/snapshot` if you also want to sync columns and record a Snapshot.
    """
    db: Session = SessionLocal()
    try:
        refresh_issues(db)
        refresh_pull_requests(db)
    finally:
        db.close()


@router.post(
    "/snapshot",
    summary=(
        "Refresh Issues/PRs, sync Project Status → Task.column_name, "
        "count by column, and insert a Snapshot"
    ),
)
def snapshot_projects_v2(
    number: int = Query(
        ...,
        description="Project number as shown in the URL (Projects v2).",
        examples=[1, 2, 42],
    ),
) -> dict:
    """Create a Kanban snapshot from a GitHub Projects v2 board.

    Steps
    -----
    1. Refresh Issues and Pull Requests (ingest from GitHub).
    2. Pull Project v2 items, read each item Status, update `Task.column_name`.
    3. Count tasks per column and persist a `Snapshot`.

    Parameters
    ----------
    number:
        The Project number (user-scoped project at `settings.github_owner`).

    Returns
    -------
    dict
        A payload like `{"updated": <int>, "counts": {"À faire": 2, "En cours": 3, ...}}`.
    """
    db: Session = SessionLocal()
    try:
        refresh_issues(db)
        refresh_pull_requests(db)
        return create_snapshot_from_project(db, number)
    finally:
        db.close()
