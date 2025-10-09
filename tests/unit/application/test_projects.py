from datetime import datetime
import src.application.projects as projects


def test_list_items_with_status_parses_single_page(monkeypatch):
    # Force a known owner and capture gql variables
    seen_vars = []
    projects.settings.github_owner = "me"

    def fake_gql(query, variables):
        seen_vars.append(variables)
        return {
            "user": {
                "projectV2": {
                    "id": "p1",
                    "title": "Proj",
                    "fields": {"nodes": []},
                    "items": {
                        "nodes": [
                            # Issue with Status
                            {
                                "id": "i1",
                                "content": {
                                    "__typename": "Issue",
                                    "number": 101,
                                    "title": "Issue A",
                                    "repository": {"name": "metrics-eq15", "owner": {"login": "owner1"}},
                                },
                                "fieldValues": {
                                    "nodes": [
                                        {
                                            "__typename": "ProjectV2ItemFieldSingleSelectValue",
                                            "field": {"id": "f", "name": "Status"},
                                            "name": "Doing",
                                            "optionId": "opt1",
                                        }
                                    ]
                                },
                            },
                            # Issue without Status
                            {
                                "id": "i2",
                                "content": {
                                    "__typename": "Issue",
                                    "number": 102,
                                    "title": "Issue B",
                                    "repository": {"name": "repo", "owner": {"login": "o"}},
                                },
                                "fieldValues": {"nodes": []},
                            },
                            # PullRequest with Status
                            {
                                "id": "i3",
                                "content": {
                                    "__typename": "PullRequest",
                                    "number": 5,
                                    "title": "PR C",
                                    "repository": {"name": "r2", "owner": {"login": "o2"}},
                                },
                                "fieldValues": {
                                    "nodes": [
                                        {
                                            "__typename": "ProjectV2ItemFieldSingleSelectValue",
                                            "field": {"id": "f", "name": "Status"},
                                            "name": "Done",
                                            "optionId": "opt2",
                                        }
                                    ]
                                },
                            },
                            # Null content
                            {"id": "i4", "content": None, "fieldValues": {"nodes": []}},
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    },
                }
            }
        }

    monkeypatch.setattr(projects, "gql", fake_gql)

    items = list(projects.list_items_with_status(project_number=2))
    assert len(items) == 4

    # Issue with status
    a = items[0]
    assert a["contentType"] == "Issue"
    assert a["issue"] == 101
    assert a["repo"] == "owner1/metrics-eq15"
    assert a["status"] == {"name": "Doing", "optionId": "opt1"}

    # Issue without status
    b = items[1]
    assert b["contentType"] == "Issue"
    assert b["issue"] == 102
    assert b["status"] is None

    # Pull request: issue field must be None, repo present, status present
    c = items[2]
    assert c["contentType"] == "PullRequest"
    assert c["issue"] is None
    assert c["repo"] == "o2/r2"
    assert c["status"] == {"name": "Done", "optionId": "opt2"}

    # Null content
    d = items[3]
    assert d["contentType"] is None
    assert d["issue"] is None
    assert d["repo"] is None
    assert d["status"] is None

    # Verify variables passed to gql
    assert seen_vars[0]["login"] == "me"
    assert seen_vars[0]["number"] == 2
    assert seen_vars[0]["after"] is None


def test_list_items_with_status_handles_pagination(monkeypatch):
    calls = []

    def fake_gql(query, variables):
        calls.append(variables["after"])
        if variables["after"] is None:
            # First page → has next
            return {
                "user": {
                    "projectV2": {
                        "id": "p",
                        "title": "T",
                        "fields": {"nodes": []},
                        "items": {
                            "nodes": [
                                {
                                    "id": "i1",
                                    "content": {
                                        "__typename": "Issue",
                                        "number": 201,
                                        "title": "A",
                                        "repository": {"name": "r", "owner": {"login": "o"}},
                                    },
                                    "fieldValues": {"nodes": []},
                                }
                            ],
                            "pageInfo": {"hasNextPage": True, "endCursor": "CURSOR_1"},
                        },
                    }
                }
            }
        else:
            # Second (last) page
            return {
                "user": {
                    "projectV2": {
                        "id": "p",
                        "title": "T",
                        "fields": {"nodes": []},
                        "items": {
                            "nodes": [
                                {
                                    "id": "i2",
                                    "content": {
                                        "__typename": "Issue",
                                        "number": 202,
                                        "title": "B",
                                        "repository": {"name": "r2", "owner": {"login": "o2"}},
                                    },
                                    "fieldValues": {"nodes": []},
                                }
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        },
                    }
                }
            }

    monkeypatch.setattr(projects, "gql", fake_gql)

    out = list(projects.list_items_with_status(project_number=9))
    nums = [it["issue"] for it in out if it["contentType"] == "Issue"]
    assert nums == [201, 202]          # both pages emitted
    assert calls == [None, "CURSOR_1"]  # after advanced across pages


def test_get_status_by_issues_filters_only_issues_with_status(monkeypatch):
    # Return a mix of Issue/PR and with/without status
    payload = [
        {"contentType": "Issue", "issue": 11, "repo": "o/r", "status": {"name": "Doing", "optionId": "x"}},
        {"contentType": "PullRequest", "issue": None, "repo": "o/r", "status": {"name": "Done", "optionId": "y"}},
        {"contentType": "Issue", "issue": 12, "repo": "o/r", "status": None},
        {"contentType": None, "issue": None, "repo": None, "status": None},
    ]
    monkeypatch.setattr(projects, "list_items_with_status", lambda number: iter(payload))

    mapping = projects.get_status_by_issues(number=42)
    assert mapping == {11: "Doing"}  # only issues that have a status are kept
