"""Use cases for refreshing data from GitHub.

This module pulls Issues and Pull Requests and upserts them into the local DB.
No business orchestration here beyond "fetch & persist".
"""

from datetime import datetime

from sqlalchemy.orm import Session

from src.config import settings
from src.database.pull_request import PullRequest
from src.database.task import Task
from src.services.github_client import list_issues, list_pull_requests


def map_issue_label_to_column(labels: list[dict]) -> str:
    names = {l["name"] for l in labels}
    for col in settings.kanban_column_names:
        if col in names:
            return col
    return "Unmapped"


def refresh_issues(db: Session):
    """Fetch issues from GitHub and upsert into `Task`.

    - Updates `state`, `title`, `closed_at`.
    - `column_name` here is only defined as Placeholder; real column name is handled in the snapshot flow using Projects v2 Status.

    Notes
    -----
    `created_at`/`closed_at` are parsed from ISO8601 strings (`Z`→UTC).
    """
    for it in list_issues():
        issue = db.query(Task).filter_by(issue_number=it["number"]).one_or_none()
        if issue is None:
            issue = Task(
                issue_number=it["number"],
                title=it["title"],
                state=it["state"],
                column_name="Placeholder",
                created_at=datetime.fromisoformat(
                    it["created_at"].replace("Z", "+00:00")
                ),
                closed_at=(
                    datetime.fromisoformat(it["closed_at"].replace("Z", "+00:00"))
                    if it.get("closed_at")
                    else None
                ),
            )
            db.add(issue)
        else:
            issue.state = it["state"]
            issue.title = it["title"]
            issue.closed_at = (
                datetime.fromisoformat(it["closed_at"].replace("Z", "+00:00"))
                if it.get("closed_at")
                else None
            )
    db.commit()


def refresh_pull_requests(db: Session):
    """Fetch pull requests from GitHub and upsert into `PullRequest`.

    - Updates timing and stat fields (`merged_at`, `closed_at`, deltas, files, counts).
    """
    for pr in list_pull_requests():
        row = db.query(PullRequest).filter_by(pr_number=pr["number"]).one_or_none()
        if row is None:
            row = PullRequest(
                pr_number=pr["number"],
                title=pr["title"],
                author=pr["user"]["login"],
                created_at=datetime.fromisoformat(
                    pr["created_at"].replace("Z", "+00:00")
                ),
                merged_at=(
                    datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                    if pr.get("merged_at")
                    else None
                ),
                closed_at=(
                    datetime.fromisoformat(pr["closed_at"].replace("Z", "+00:00"))
                    if pr.get("closed_at")
                    else None
                ),
                head_branch=pr["head"]["ref"],
                base_branch=pr["base"]["ref"],
                additions=pr.get("additions", 0),
                deletions=pr.get("deletions", 0),
                changed_files=pr.get("changed_files", 0),
                reviews=len(pr["_reviews"]),
                commits=len(pr["_commits"]),
            )
            db.add(row)
        else:
            row.title = pr["title"]
            row.merged_at = (
                datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                if pr.get("merged_at")
                else None
            )
            row.closed_at = (
                datetime.fromisoformat(pr["closed_at"].replace("Z", "+00:00"))
                if pr.get("closed_at")
                else None
            )
            row.head_branch = pr["head"]["ref"]
            row.base_branch = pr["base"]["ref"]
            row.additions = pr.get("additions", 0)
            row.deletions = pr.get("deletions", 0)
            row.changed_files = pr.get("changed_files", 0)
            row.reviews = len(pr["_reviews"])
            row.commits = len(pr["_commits"])
    db.commit()
