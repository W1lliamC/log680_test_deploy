from datetime import datetime, timedelta

import pytest

import src.services.db as db
from src.database.pull_request import PullRequest


def _insert_pr(sess, **data):
    """Insert a PullRequest using only valid model columns (future-proof)."""
    cols = set(PullRequest.__table__.columns.keys())
    sess.add(PullRequest(**{k: v for k, v in data.items() if k in cols}))


def _reset_and_seed():
    """
    Wipe PullRequest rows, then insert one merged/closed PR and one open PR.
    Use NAIVE datetimes (SQLite drops tz info).
    """
    sess = db.SessionLocal()
    try:
        now = datetime.utcnow()

        # clean slate
        sess.query(PullRequest).delete()
        sess.commit()

        # merged/closed PR
        _insert_pr(
            sess,
            pr_number=201,
            title="PR merged",
            author="alice",
            created_at=now - timedelta(days=9),
            merged_at=now - timedelta(days=4),
            closed_at=now - timedelta(days=4),
            additions=100,
            deletions=20,
            changed_files=3,
            reviews=2,
            commits=5,
            head_branch="feature/x",
            base_branch="main",
        )
        # open PR (no merged_at / closed_at)
        _insert_pr(
            sess,
            pr_number=202,
            title="PR open",
            author="bob",
            created_at=now - timedelta(days=2),
            merged_at=None,
            closed_at=None,
            additions=10,
            deletions=2,
            changed_files=1,
            reviews=0,
            commits=1,
            head_branch="bugfix/y",
            base_branch="develop",
        )
        sess.commit()
        return now
    finally:
        sess.close()


def test_pr_lead_time_404_when_missing(client):
    r = client.get("/metrics/prs/lead-time/999999")
    assert r.status_code == 404
    assert "Non existent" in r.text or "Not Found" in r.text


def test_pr_lead_time_open_and_closed(client, monkeypatch):
    _reset_and_seed()

    # closed/merged → lead_time present (>0), age None/absent
    r = client.get("/metrics/prs/lead-time/201")
    assert r.status_code == 200
    b = r.json()
    assert "lead_time" in b and (b["lead_time"] is not None) and (b["lead_time"] > 0)
    assert ("age" not in b) or (b["age"] in (None, 0))

    import src.application.schemas as schemas

    class _NaiveDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.utcnow()

    monkeypatch.setattr(schemas, "datetime", _NaiveDT)

    r = client.get("/metrics/prs/lead-time/202")
    assert r.status_code == 200
    b = r.json()
    assert ("lead_time" not in b) or (b["lead_time"] is None)
    assert b.get("age") is not None and b["age"] > 0


def test_pr_lead_time_list_filters_by_window(client):
    now = _reset_and_seed()

    # window including merged/closed (~4 days ago)
    r = client.get(
        "/metrics/prs/lead-time",
        params={"start": (now - timedelta(days=6)).isoformat(), "end": now.isoformat()},
    )
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    assert any(it["pr_number"] == 201 for it in items)

    # window excluding it
    r = client.get(
        "/metrics/prs/lead-time",
        params={
            "start": (now - timedelta(days=20)).isoformat(),
            "end": (now - timedelta(days=10, minutes=1)).isoformat(),
        },
    )
    assert r.status_code == 200
    assert r.json() == []


def test_pr_commits_and_reviews_counts(client):
    _reset_and_seed()

    # commits
    r = client.get("/metrics/prs/commits/201")
    assert r.status_code == 200
    assert r.json()["count"] == 5

    # reviews
    r = client.get("/metrics/prs/reviews/201")
    assert r.status_code == 200
    assert r.json()["count"] == 2


def test_pr_stats_returns_add_del_changed(client):
    _reset_and_seed()
    r = client.get("/metrics/prs/stats/201")
    assert r.status_code == 200
    stats = r.json()
    assert stats["additions"] == 100
    assert stats["deletions"] == 20
    assert stats["changed_files"] == 3


def test_pr_branches_ok_and_404(client):
    _reset_and_seed()

    r = client.get("/metrics/prs/branches/201")
    assert r.status_code == 200
    br = r.json()
    assert br["head"] == "feature/x"
    assert br["base"] == "main"

    r = client.get("/metrics/prs/branches/999999")
    assert r.status_code == 404
    assert "Non existent" in r.text or "Not Found" in r.text


@pytest.mark.parametrize(
    "path",
    [
        "/metrics/prs/commits/999999",
        "/metrics/prs/reviews/999999",
        "/metrics/prs/stats/999999",
    ],
)
def test_pr_detail_endpoints_404_for_missing_pr(client, path):
    r = client.get(path)
    assert r.status_code == 404
