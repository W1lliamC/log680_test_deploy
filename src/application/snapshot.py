"""Snapshot creation use-case.

Refreshes Project Status into Task.column_name, computes counts per column,
and persists a Snapshot row.
"""

from datetime import datetime
from typing import Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.application.projects import get_status_by_issues
from src.database.snapshot import Snapshot
from src.database.task import Task


def create_snapshot_from_project(db: Session, number: int) -> Dict[str, object]:
    """Create a snapshot of the Kanban state from a Projects v2 board.

    Parameters
    ----------
    db : Session
        SQLAlchemy session.
    number : int
        Project number (user-scoped).

    Returns
    -------
    dict
        {
          "updated": <int>,       # how many Task rows we set column_name for
          "counts": {"À faire": 2, "En cours": 3, "Terminée": 7, ...}
        }
    """
    # 1) Fetch items with status
    statuses = get_status_by_issues(number)

    # 2) Update tasks that match (single loop; okay for moderate sizes)
    updated = 0
    for issue_num, label in statuses.items():
        row = db.query(Task).filter_by(issue_number=issue_num).one_or_none()
        if row and row.column_name != label:
            row.column_name = label
            updated += 1

    db.commit()

    # 3) Count tasks per column (total; include closed unless you filter)
    rows = db.query(Task.column_name, func.count()).group_by(Task.column_name).all()
    counts = {label: cnt for label, cnt in rows if label is not None}

    # 4) Persist snapshot
    snap = Snapshot(ts=datetime.utcnow(), counts=counts)
    db.add(snap)
    db.commit()
    db.refresh(snap)

    return {"updated": updated, "counts": counts}
