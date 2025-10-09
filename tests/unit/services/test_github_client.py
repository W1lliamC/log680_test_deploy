import types
import pytest
import requests

import src.services.github_client as client

# _token()

def test__token_returns_value(monkeypatch):
    # Patch the settings object on the imported module itself
    monkeypatch.setattr(
        client,
        "settings",
        types.SimpleNamespace(github_token="tok-123"),
        raising=False,
    )
    # sanity
    assert client.settings.github_token == "tok-123"

    assert client._token() == "tok-123"


def test__token_raises_when_missing(monkeypatch):
    monkeypatch.setattr(
        client,
        "settings",
        types.SimpleNamespace(github_token=""),
        raising=False,
    )
    # sanity
    assert client.settings.github_token == ""

    with pytest.raises(RuntimeError, match="GITHUB_TOKEN not set"):
        client._token()


# _headers()

def test__headers_includes_auth_and_accept(monkeypatch):
    monkeypatch.setattr(
        client,
        "settings",
        types.SimpleNamespace(github_token="abc"),
        raising=False,
    )
    # sanity
    assert client.settings.github_token == "abc"

    h = client._headers()
    assert "Authorization" in h and h["Authorization"].startswith("Bearer ")
    assert h.get("Accept") == "application/vnd.github+json"


# gql()

class FakeResp:
    def __init__(self, status=200, json_data=None, links=None):
        self.status_code = status
        self._json = {} if json_data is None else json_data
        self.links = {} if links is None else links

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error", response=self)


def test_gql_success(monkeypatch):
    # Ensure _token() succeeds by patching the in-module settings
    monkeypatch.setattr(
        client,
        "settings",
        types.SimpleNamespace(github_token="t"),
        raising=False,
    )
    # sanity
    assert client.settings.github_token == "t"

    calls = {}

    def fake_post(url, json, headers, timeout):
        calls["url"] = url
        calls["json"] = json
        calls["headers"] = headers
        calls["timeout"] = timeout
        return FakeResp(200, {"data": {"ok": 1}})

    monkeypatch.setattr(requests, "post", fake_post)

    out = client.gql("query Q{}", {"v": 1})
    assert out == {"ok": 1}
    assert calls["url"].endswith("/graphql")
    assert calls["json"] == {"query": "query Q{}", "variables": {"v": 1}}
    assert calls["headers"]["Authorization"].startswith("Bearer ")
    assert calls["timeout"] == 30


def test_gql_http_error_raises(monkeypatch):
    monkeypatch.setattr(
        client,
        "settings",
        types.SimpleNamespace(github_token="t"),
        raising=False,
    )
    # sanity
    assert client.settings.github_token == "t"

    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResp(401, {"message": "nope"}))
    with pytest.raises(requests.HTTPError):
        client.gql("q{}", {})


def test_gql_graphql_error_field_raises(monkeypatch):
    monkeypatch.setattr(
        client,
        "settings",
        types.SimpleNamespace(github_token="t"),
        raising=False,
    )
    # sanity
    assert client.settings.github_token == "t"

    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResp(200, {"errors": [{"msg": "bad"}]}))
    with pytest.raises(RuntimeError):
        client.gql("q{}", {})


# _paginate()

def test__paginate_single_page_yields_items_and_uses_params_and_headers(monkeypatch):
    # Avoid token usage by patching _headers directly here
    monkeypatch.setattr(client, "_headers", lambda: {"X": "Y"})

    calls = []

    def fake_get(url, headers=None, params=None, **kw):
        calls.append((url, headers, dict(params or {})))
        return FakeResp(200, json_data=[{"id": 1}, {"id": 2}], links={})

    monkeypatch.setattr(requests, "get", fake_get)

    url = "https://api.github.com/anything"
    items = list(client._paginate(url, params={"state": "all", "per_page": 10}))
    assert items == [{"id": 1}, {"id": 2}]
    # Assert request details
    assert calls[0][0] == url
    assert calls[0][1] == {"X": "Y"}
    assert calls[0][2] == {"state": "all", "per_page": 10}


def test__paginate_follows_next_link(monkeypatch):
    monkeypatch.setattr(client, "_headers", lambda: {})

    seen_urls = []

    def fake_get(url, headers=None, params=None, **kw):
        seen_urls.append(url)
        if len(seen_urls) == 1:
            return FakeResp(200, json_data=[{"a": 1}], links={"next": {"url": "http://next"}})
        else:
            return FakeResp(200, json_data=[{"b": 2}], links={})

    monkeypatch.setattr(requests, "get", fake_get)

    out = list(client._paginate("http://first", params={"x": 1}))
    assert out == [{"a": 1}, {"b": 2}]
    assert seen_urls == ["http://first", "http://next"]


# list_issues()

def test_list_issues_filters_out_pull_requests_and_uses_owner_repo(monkeypatch):
    # Patch owner/repo/token in the module under test
    monkeypatch.setattr(
        client,
        "settings",
        types.SimpleNamespace(github_owner="me", github_repo="repo", github_token="t"),
        raising=False,
    )
    # sanity
    assert client.settings.github_owner == "me"
    assert client.settings.github_repo == "repo"
    assert client.settings.github_token == "t"

    captured = {}

    def fake_paginate(url, params=None):
        captured["url"] = url
        captured["params"] = dict(params or {})
        # include a real issue and two items that look like PRs (should be filtered out)
        yield {"number": 10, "title": "Issue", "state": "open"}
        yield {"number": 11, "pull_request": {"url": "..."}}
        yield {"number": 12, "title": "Another", "pull_request": {}}

    monkeypatch.setattr(client, "_paginate", fake_paginate)

    out = list(client.list_issues())
    assert [i["number"] for i in out] == [10]  # only real issues remain
    assert captured["url"] == f"{client.BASE}/repos/me/repo/issues"
    assert captured["params"] == {"state": "all", "per_page": 100}


# list_pull_requests()

def test_list_pull_requests_fetches_details_reviews_commits_and_attaches(monkeypatch):
    # Patch owner/repo/token in the module under test
    monkeypatch.setattr(
        client,
        "settings",
        types.SimpleNamespace(github_owner="acme", github_repo="proj", github_token="t"),
        raising=False,
    )
    # sanity
    assert client.settings.github_owner == "acme"
    assert client.settings.github_repo == "proj"
    assert client.settings.github_token == "t"

    # Ensure headers is stable and visible to our fake requests.get
    monkeypatch.setattr(client, "_headers", lambda: {"Auth": "yes"})

    # 1) The main list of PRs comes from _paginate (numbers only are enough)
    monkeypatch.setattr(client, "_paginate", lambda url, params=None: iter([{"number": 1}, {"number": 2}]))

    # 2) For each PR number, the code hits three endpoints: details, reviews, commits
    calls = {"urls": []}

    def make_json_obj(data):
        return types.SimpleNamespace(json=lambda: data)

    def fake_get(url, headers=None, **kw):
        # Validate headers flow
        assert headers == {"Auth": "yes"}
        calls["urls"].append(url)

        if url.endswith("/pulls/1"):
            return make_json_obj({
                "number": 1,
                "title": "PR-1",
                "user": {"login": "alice"},
                "created_at": "2025-01-01T00:00:00Z",
                "merged_at": None,
                "closed_at": None,
                "head": {"ref": "feat/a"},
                "base": {"ref": "main"},
            })
        if url.endswith("/pulls/1/reviews"):
            return make_json_obj([{"id": "r1"}])
        if url.endswith("/pulls/1/commits"):
            return make_json_obj([{"sha": "c1"}, {"sha": "c2"}])

        if url.endswith("/pulls/2"):
            return make_json_obj({
                "number": 2,
                "title": "PR-2",
                "user": {"login": "bob"},
                "created_at": "2025-01-02T00:00:00Z",
                "merged_at": "2025-01-03T00:00:00Z",
                "closed_at": "2025-01-03T00:00:00Z",
                "head": {"ref": "bug/b"},
                "base": {"ref": "develop"},
            })
        if url.endswith("/pulls/2/reviews"):
            return make_json_obj([])
        if url.endswith("/pulls/2/commits"):
            return make_json_obj([{"sha": "c3"}])

        raise AssertionError(f"Unexpected URL {url}")

    monkeypatch.setattr(requests, "get", fake_get)

    prs = list(client.list_pull_requests())
    # Both PRs returned
    assert [p["number"] for p in prs] == [1, 2]

    # _reviews/_commits attached with correct counts
    p1, p2 = prs
    assert p1["title"] == "PR-1" and len(p1["_reviews"]) == 1 and len(p1["_commits"]) == 2
    assert p2["title"] == "PR-2" and len(p2["_reviews"]) == 0 and len(p2["_commits"]) == 1

    # Sanity: we hit the expected detail endpoints
    base = f"{client.BASE}/repos/acme/proj/pulls"
    assert set(calls["urls"]) == {
        f"{base}/1",
        f"{base}/1/reviews",
        f"{base}/1/commits",
        f"{base}/2",
        f"{base}/2/reviews",
        f"{base}/2/commits",
    }
