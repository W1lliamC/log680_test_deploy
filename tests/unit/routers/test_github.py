import pytest

def test_refresh_calls_ingest_and_returns_200(client, monkeypatch):
    import src.routers.github as gh

    calls = {"issues": 0, "prs": 0}

    def fake_refresh_issues(db):
        calls["issues"] += 1

    def fake_refresh_prs(db):
        calls["prs"] += 1

    monkeypatch.setattr(gh, "refresh_issues", fake_refresh_issues)
    monkeypatch.setattr(gh, "refresh_pull_requests", fake_refresh_prs)

    r = client.post("/refresh")
    assert r.status_code == 200
    assert calls["issues"] == 1
    assert calls["prs"] == 1


def test_snapshot_calls_refresh_and_snapshot_returns_payload(client, monkeypatch):
    import src.routers.github as gh

    calls = {"issues": 0, "prs": 0, "snap": 0, "snap_args": []}

    def fake_refresh_issues(db):
        calls["issues"] += 1

    def fake_refresh_prs(db):
        calls["prs"] += 1

    def fake_create_snapshot(db, number: int):
        calls["snap"] += 1
        calls["snap_args"].append(number)
        return {"updated": 0, "counts": {"Doing": 1, "Done": 2}}

    monkeypatch.setattr(gh, "refresh_issues", fake_refresh_issues)
    monkeypatch.setattr(gh, "refresh_pull_requests", fake_refresh_prs)
    monkeypatch.setattr(gh, "create_snapshot_from_project", fake_create_snapshot)

    r = client.post("/snapshot", params={"number": 2})
    assert r.status_code == 200

    body = r.json()
    assert body == {"updated": 0, "counts": {"Doing": 1, "Done": 2}}

    assert calls["issues"] == 1
    assert calls["prs"] == 1
    assert calls["snap"] == 1
    assert calls["snap_args"] == [2]


def test_snapshot_requires_number_param(client):
    # FastAPI should validate and return 422 if 'number' is missing
    r = client.post("/snapshot")
    assert r.status_code == 422
