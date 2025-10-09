from datetime import datetime, timedelta

import src.application.refresh as refresh
import src.services.db as db
from src.database.pull_request import PullRequest
from src.database.task import Task

# map_issue_label_to_column


def test_map_issue_label_to_column_matches_first_in_settings(monkeypatch):
    # Order matters: first matching column in settings.kanban_column_names wins
    class _S:
        kanban_column_names = ["To Do", "Doing", "Done"]

    monkeypatch.setattr(refresh, "settings", _S, raising=False)

    # Labels contain two matches → expect the first in settings order ("Doing")
    labels = [{"name": "Bug"}, {"name": "Doing"}, {"name": "Done"}]
    assert refresh.map_issue_label_to_column(labels) == "Doing"


def test_map_issue_label_to_column_returns_unmapped_when_no_match(monkeypatch):
    class _S:
        kanban_column_names = ["To Do", "Doing", "Done"]

    monkeypatch.setattr(refresh, "settings", _S, raising=False)

    labels = [{"name": "Enhancement"}, {"name": "Infra"}]
    assert refresh.map_issue_label_to_column(labels) == "Unmapped"


# refresh_issues (insert + update)


def _wipe_tasks():
    s = db.SessionLocal()
    try:
        s.query(Task).delete()
        s.commit()
    finally:
        s.close()


def test_refresh_issues_inserts_and_updates(monkeypatch):
    _wipe_tasks()
    now = datetime.utcnow().replace(microsecond=0)

    # 1) initial fetch → insert two issues (one open, one closed)
    def fake_list_issues_first():
        return [
            {
                "number": 101,
                "title": "A",
                "state": "open",
                "created_at": (now - timedelta(days=5)).isoformat() + "Z",
                "closed_at": None,
            },
            {
                "number": 102,
                "title": "B",
                "state": "closed",
                "created_at": (now - timedelta(days=10)).isoformat() + "Z",
                "closed_at": (now - timedelta(days=1)).isoformat() + "Z",
            },
        ]

    monkeypatch.setattr(refresh, "list_issues", fake_list_issues_first)

    s = db.SessionLocal()
    try:
        refresh.refresh_issues(s)
        rows = s.query(Task).order_by(Task.issue_number).all()
        assert [r.issue_number for r in rows] == [101, 102]
        # placeholder column on insert
        assert all(r.column_name == "Placeholder" for r in rows)
        # open vs closed timestamps
        a, b = rows
        assert a.closed_at is None
        assert b.closed_at is not None
    finally:
        s.close()

    # 2) second fetch → update fields (title/state/closed_at)
    def fake_list_issues_second():
        return [
            {
                "number": 101,
                "title": "A (edited)",
                "state": "closed",
                "created_at": (now - timedelta(days=5)).isoformat() + "Z",
                "closed_at": (now - timedelta(days=2)).isoformat() + "Z",
            },
            {
                "number": 102,
                "title": "B (edited)",
                "state": "closed",
                "created_at": (now - timedelta(days=10)).isoformat() + "Z",
                "closed_at": (now - timedelta(days=1)).isoformat() + "Z",
            },
        ]

    monkeypatch.setattr(refresh, "list_issues", fake_list_issues_second)

    s = db.SessionLocal()
    try:
        refresh.refresh_issues(s)
        r101 = s.query(Task).filter_by(issue_number=101).one()
        r102 = s.query(Task).filter_by(issue_number=102).one()
        assert r101.title == "A (edited)"
        assert r101.state == "closed"
        assert r101.closed_at is not None
        assert r102.title == "B (edited)"
    finally:
        s.close()


# refresh_pull_requests (insert + update)


def _wipe_prs():
    s = db.SessionLocal()
    try:
        s.query(PullRequest).delete()
        s.commit()
    finally:
        s.close()


def test_refresh_pull_requests_inserts_and_updates(monkeypatch):
    _wipe_prs()
    now = datetime.utcnow().replace(microsecond=0)

    # 1) initial fetch → insert merged + open PRs
    def fake_list_prs_first():
        return [
            {
                "number": 201,
                "title": "PR merged",
                "user": {"login": "alice"},
                "created_at": (now - timedelta(days=9)).isoformat() + "Z",
                "merged_at": (now - timedelta(days=4)).isoformat() + "Z",
                "closed_at": (now - timedelta(days=4)).isoformat() + "Z",
                "head": {"ref": "feature/x"},
                "base": {"ref": "main"},
                "additions": 100,
                "deletions": 20,
                "changed_files": 3,
                "_reviews": [1, 2],
                "_commits": [1, 2, 3, 4, 5],
            },
            {
                "number": 202,
                "title": "PR open",
                "user": {"login": "bob"},
                "created_at": (now - timedelta(days=2)).isoformat() + "Z",
                "merged_at": None,
                "closed_at": None,
                "head": {"ref": "bugfix/y"},
                "base": {"ref": "develop"},
                "additions": 10,
                "deletions": 2,
                "changed_files": 1,
                "_reviews": [],
                "_commits": [1],
            },
        ]

    monkeypatch.setattr(refresh, "list_pull_requests", fake_list_prs_first)

    s = db.SessionLocal()
    try:
        refresh.refresh_pull_requests(s)
        prs = s.query(PullRequest).order_by(PullRequest.pr_number).all()
        assert [p.pr_number for p in prs] == [201, 202]
        p201, p202 = prs
        assert p201.reviews == 2 and p201.commits == 5
        assert p201.head_branch == "feature/x" and p201.base_branch == "main"
        assert p202.merged_at is None and p202.closed_at is None
    finally:
        s.close()

    # 2) update fetch → change fields on 201 and 202
    def fake_list_prs_second():
        return [
            {
                "number": 201,
                "title": "PR merged (edited)",
                "user": {"login": "alice"},
                "created_at": (now - timedelta(days=9)).isoformat() + "Z",
                "merged_at": (now - timedelta(days=3)).isoformat() + "Z",
                "closed_at": (now - timedelta(days=3)).isoformat() + "Z",
                "head": {"ref": "feature/x2"},
                "base": {"ref": "main"},
                "additions": 110,
                "deletions": 25,
                "changed_files": 4,
                "_reviews": [1, 2, 3],
                "_commits": [1, 2, 3, 4, 5, 6],
            },
            {
                "number": 202,
                "title": "PR open (edited)",
                "user": {"login": "bob"},
                "created_at": (now - timedelta(days=2)).isoformat() + "Z",
                "merged_at": None,
                "closed_at": (now - timedelta(days=1)).isoformat() + "Z",  # now closed
                "head": {"ref": "bugfix/y"},
                "base": {"ref": "develop"},
                "additions": 12,
                "deletions": 3,
                "changed_files": 2,
                "_reviews": [1],
                "_commits": [1, 2],
            },
        ]

    monkeypatch.setattr(refresh, "list_pull_requests", fake_list_prs_second)

    s = db.SessionLocal()
    try:
        refresh.refresh_pull_requests(s)
        p201 = s.query(PullRequest).filter_by(pr_number=201).one()
        p202 = s.query(PullRequest).filter_by(pr_number=202).one()
        assert p201.title == "PR merged (edited)"
        assert p201.reviews == 3 and p201.commits == 6
        assert p201.head_branch == "feature/x2"
        assert p202.closed_at is not None  # became closed
        assert p202.additions == 12 and p202.changed_files == 2
    finally:
        s.close()
