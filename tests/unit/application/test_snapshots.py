from datetime import datetime, timedelta

import src.application.snapshot as snap
import src.services.db as db
from src.database.snapshot import Snapshot
from src.database.task import Task


def _add_task(sess, **kwargs):
    cols = set(Task.__table__.columns.keys())
    sess.add(Task(**{k: v for k, v in kwargs.items() if k in cols}))


def test_create_snapshot_hits_update_counts_persist(monkeypatch):
    s = db.SessionLocal()
    try:
        s.query(Snapshot).delete()
        s.query(Task).delete()
        s.commit()

        now = datetime.utcnow().replace(microsecond=0)

        # Seed tasks:
        #  - #1 will change from "To Do" -> "Doing"
        #  - #3 will change from "Review" -> "Done" (avoid NULL to satisfy NOT NULL constraint)
        #  - #4 remains "Backlog"
        _add_task(
            s,
            issue_number=1,
            title="A",
            state="open",
            column_name="To Do",
            created_at=now - timedelta(days=5),
        )
        _add_task(
            s,
            issue_number=3,
            title="C",
            state="closed",
            column_name="Review",
            created_at=now - timedelta(days=10),
            closed_at=now - timedelta(days=1),
        )
        _add_task(
            s,
            issue_number=4,
            title="D",
            state="open",
            column_name="Backlog",
            created_at=now - timedelta(days=2),
        )
        s.commit()

        # Drive update + counts + snapshot paths
        monkeypatch.setattr(
            snap,
            "get_status_by_issues",
            lambda number: {1: "Doing", 3: "Done", 999: "Ignored"},
        )

        res = snap.create_snapshot_from_project(s, number=2)

        # updated count
        assert res["updated"] == 2
        # aggregated counts (exclude None)
        assert res["counts"] == {"Doing": 1, "Done": 1, "Backlog": 1}

        # DB rows updated
        assert s.query(Task).filter_by(issue_number=1).one().column_name == "Doing"
        assert s.query(Task).filter_by(issue_number=3).one().column_name == "Done"

        # Snapshot persisted
        snaps = s.query(Snapshot).order_by(Snapshot.id).all()
        assert len(snaps) == 1
        assert snaps[0].counts == res["counts"]
    finally:
        s.close()
