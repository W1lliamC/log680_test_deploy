from typing import Iterable

import requests

from src.config import settings

BASE = "https://api.github.com"


def _token() -> str:
    tok = settings.github_token
    if not tok:
        raise RuntimeError("GITHUB_TOKEN not set")
    return tok


def _headers():
    return {
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/vnd.github+json",
    }


def gql(query: str, variables: dict):
    r = requests.post(
        BASE + "/graphql",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"Bearer {_token()}"},
        timeout=30,
    )
    r.raise_for_status()
    j = r.json()
    if "errors" in j:
        raise RuntimeError(j["errors"])
    return j["data"]


def _paginate(url: str, params: dict | None = None) -> Iterable[dict]:
    params = params or {}
    while url:
        r = requests.get(url, headers=_headers(), params=params)
        r.raise_for_status()
        yield from r.json()
        url = r.links.get("next", {}).get("url")


def list_issues():
    # Issues seulement (exclut PRs) : filtre en enlevant ceux qui ont "pull_request"
    url = f"{BASE}/repos/{settings.github_owner}/{settings.github_repo}/issues"
    for item in _paginate(url, {"state": "all", "per_page": 100}):
        if "pull_request" in item:  # PR déguisée en issue
            continue
        yield item


def list_pull_requests():
    url = f"{BASE}/repos/{settings.github_owner}/{settings.github_repo}/pulls"
    for pr in _paginate(url, {"state": "all", "per_page": 100}):
        # détails supplémentaires
        prd = requests.get(
            f"{BASE}/repos/{settings.github_owner}/{settings.github_repo}/pulls/{pr['number']}",
            headers=_headers(),
        ).json()
        reviews = requests.get(
            f"{BASE}/repos/{settings.github_owner}/{settings.github_repo}/pulls/{pr['number']}/reviews",
            headers=_headers(),
        ).json()
        commits = requests.get(
            f"{BASE}/repos/{settings.github_owner}/{settings.github_repo}/pulls/{pr['number']}/commits",
            headers=_headers(),
        ).json()
        prd["_reviews"] = reviews
        prd["_commits"] = commits
        yield prd
