"""Project (v2) accessors.

Light wrappers around GraphQL queries to enumerate project items and read
their Status single-select value.
"""

from typing import Dict, Iterator

from src.config import settings
from src.services.github_client import gql

# GraphQL: user-scoped Projects v2. Swap `user(...)` to `organization(...)`
# if needed and adjust the traversal accordingly.
QUERY_ITEMS_WITH_STATUS = """
query ItemsWithStatus($login:String!, $number:Int!, $after:String){
  user(login:$login){
    projectV2(number:$number){
      id title
      fields(first:50){
        nodes{
          __typename
          ... on ProjectV2SingleSelectField{
            id name options{id name}
          }
        }
      }
      items(first:100, after:$after){
        nodes{
          id
          content{
            __typename
            ... on Issue{ id number title repository{name owner{login}} }
            ... on PullRequest{ id number title repository{name owner{login}} }
          }
          fieldValues(first:20){
            nodes{
              __typename
              ... on ProjectV2ItemFieldSingleSelectValue{
                field{ ... on ProjectV2SingleSelectField{ id name } }
                name
                optionId
              }
            }
          }
        }
        pageInfo{ hasNextPage endCursor }
      }
    }
  }
}
"""


def list_items_with_status(project_number: int) -> Iterator[dict]:
    """Yield Project items with their Status (if present).

    Parameters
    ----------
    project_number : int

    Yields
    ------
    dict
        Example:
        {
          "itemId": "...",
          "contentType": "Issue" | "PullRequest" | None,
          "issue": 123 | None,
          "repo": "owner/repo" | None,
          "status": {"name": "En cours", "optionId": "47fc9ee4"} | None
        }
    """
    after = None
    user_login = settings.github_owner

    while True:
        data = gql(
            QUERY_ITEMS_WITH_STATUS,
            {"login": user_login, "number": project_number, "after": after},
        )
        proj = data["user"]["projectV2"]

        for it in proj["items"]["nodes"]:
            status = None
            for fv in it["fieldValues"]["nodes"]:
                if (
                    fv["__typename"] == "ProjectV2ItemFieldSingleSelectValue"
                    and fv["field"]["name"] == "Status"
                ):
                    status = {"name": fv["name"], "optionId": fv["optionId"]}
                    break

            yield {
                "itemId": it["id"],
                "contentType": it["content"]["__typename"] if it["content"] else None,
                "issue": (
                    it["content"]["number"]
                    if it["content"] and it["content"]["__typename"] == "Issue"
                    else None
                ),
                "repo": (
                    f"{it['content']['repository']['owner']['login']}/{it['content']['repository']['name']}"
                    if it["content"]
                    else None
                ),
                "status": status,
            }

        pg = proj["items"]["pageInfo"]
        if not pg["hasNextPage"]:
            break
        after = pg["endCursor"]


def get_status_by_issues(number: int) -> Dict[int, str]:
    """Return a mapping `{issue_number -> Status name}` for a Projects v2 board.

    Parameters
    ----------
    number : int
        Project number as shown in the GitHub UI.

    Returns
    -------
    dict[int, str]
        Example: `{15: "En cours", 16: "Terminée", ...}`.
        Only includes items that are issues *and* have a Status value.
    """
    status_by_issue: Dict[int, str] = {}

    for it in list_items_with_status(number):
        if it["contentType"] != "Issue" or it["issue"] is None or it["status"] is None:
            continue
        status_by_issue[int(it["issue"])] = it["status"]["name"]

    return status_by_issue
