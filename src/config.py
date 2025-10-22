import os

from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel

load_dotenv(find_dotenv())


class Settings(BaseModel):
    port: int = int(os.getenv("PORT", "8080"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    github_token: str = os.getenv("TOKEN_GITHUB")
    github_owner: str = os.getenv("OWNER_GITHUB", "")
    github_repo: str = os.getenv("REPO_GITHUB", "")

    kanban_done_label: str = os.getenv("KANBAN_DONE_LABEL", "Done")
    kanban_doing_label: str = os.getenv("KANBAN_DOING_LABEL", "Doing")
    kanban_todo_label: str = os.getenv("KANBAN_TODO_LABEL", "To Do")
    kanban_column_names: list[str] = [
        "Backlog",
        "À faire",
        "En cours",
        "En revue",
        "Terminée",
    ]

    postgres_dsn: str | None = os.getenv("POSTGRES_DSN")
    sqlite_dsn: str | None = os.getenv("SQLITE_DSN")  # option dev


settings = Settings()
