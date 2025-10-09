# tests/unit/routers/test_kanban.py

from datetime import datetime, timedelta

import src.services.db as db
from src.database.snapshot import Snapshot
from src.database.task import Task


def _insert_task(sess, **data):
    """Insert a Task using only valid model columns (future-proof)."""
    cols = set(Task.__table__.columns.keys())
    sess.add(Task(**{k: v for k, v in data.items() if k in cols}))


def _reset_and_seed():
    """
    Wipe Tasks/Snapshots, then insert one open + one closed task.
    Use NAIVE datetimes (SQLite drops tz info), so avoid timezone-aware datetimes.
    """
    sess = db.SessionLocal()
    try:
        now = datetime.utcnow()

        # clean slate
        try:
            sess.query(Snapshot).delete()
        except Exception:
            pass
        sess.query(Task).delete()
        sess.commit()

        # open task (no closed_at)
        _insert_task(
            sess,
            issue_number=1001,
            title="Open task",
            state="open",
            column_name="Doing",
            created_at=now - timedelta(days=2),
            closed_at=None,
        )

        # closed task (has closed_at)
        _insert_task(
            sess,
            issue_number=1002,
            title="Closed task",
            state="closed",
            column_name="Done",
            created_at=now - timedelta(days=10),
            closed_at=now - timedelta(days=3),
        )

        sess.commit()
        return now
    finally:
        sess.close()


def test_get_issue_lead_time_404_when_missing(client):
    r = client.get("/metrics/kanban/lead-time/999999")
    assert r.status_code == 404

    assert "Non existent" in r.text or "Not Found" in r.text


def test_get_issue_lead_time_open_and_closed(client, monkeypatch):
    _reset_and_seed()

    # closed → lead_time present (>0), age absent or None
    r = client.get("/metrics/kanban/lead-time/1002")
    assert r.status_code == 200
    b = r.json()
    assert "lead_time" in b and (b["lead_time"] is not None) and (b["lead_time"] > 0)
    assert ("age" not in b) or (b["age"] in (None, 0))

    import src.application.schemas as schemas

    class _NaiveDT(datetime):
        @classmethod
        def now(cls, tz=None):
            # ignore tz and return naive UTC
            return datetime.utcnow()

    monkeypatch.setattr(schemas, "datetime", _NaiveDT)

    # open → lead_time None/absent, age present (>0)
    r = client.get("/metrics/kanban/lead-time/1001")
    assert r.status_code == 200
    b = r.json()
    assert ("lead_time" not in b) or (b["lead_time"] is None)
    assert b.get("age") is not None and b["age"] > 0


def test_list_issue_lead_times_filters_by_window(client):
    now = _reset_and_seed()

    # window that includes the closed task (closed ~3 days ago)
    r = client.get(
        "/metrics/kanban/lead-time",
        params={"start": (now - timedelta(days=5)).isoformat(), "end": now.isoformat()},
    )
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert any(it["issue_number"] == 1002 for it in items)

    # window that excludes it
    r = client.get(
        "/metrics/kanban/lead-time",
        params={
            "start": (now - timedelta(days=20)).isoformat(),
            "end": (now - timedelta(days=10, minutes=1)).isoformat(),
        },
    )
    assert r.status_code == 200
    assert r.json() == []


def test_active_count_for_column_and_all(client):
    _reset_and_seed()

    # column=Doing has one open task
    r = client.get("/metrics/kanban/active-count", params={"column": "Doing"})
    assert r.status_code == 200
    body = r.json()
    assert body["column"] == "Doing"
    assert body["count"] == 1

    # column with no open tasks returns count 0
    r = client.get("/metrics/kanban/active-count", params={"column": "Backlog"})
    assert r.status_code == 200
    assert r.json()["count"] == 0

    # no column → list of columns with active counts (Doing should be present)
    r = client.get("/metrics/kanban/active-count")
    assert r.status_code == 200
    lst = r.json()
    assert isinstance(lst, list)
    assert any(item["column"] == "Doing" and item["count"] == 1 for item in lst)


def test_completed_count_total_and_window(client):
    now = _reset_and_seed()

    # total closed issues
    r = client.get("/metrics/kanban/completed-count")
    assert r.status_code == 200
    total = r.json()
    assert isinstance(total, int)
    assert total >= 1

    # window that includes the closed task
    r = client.get(
        "/metrics/kanban/completed-count",
        params={"start": (now - timedelta(days=5)).isoformat(), "end": now.isoformat()},
    )
    assert r.status_code == 200
    assert r.json() >= 1

    # window that excludes it
    r = client.get(
        "/metrics/kanban/completed-count",
        params={
            "start": (now - timedelta(days=20)).isoformat(),
            "end": (now - timedelta(days=10, minutes=1)).isoformat(),
        },
    )
    assert r.status_code == 200
    assert r.json() == 0
