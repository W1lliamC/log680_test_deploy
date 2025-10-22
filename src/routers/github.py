"""Github endpoints.

These endpoints orchestrate data refreshes from GitHub and creation of snapshots.
They are intentionally thin: HTTP concerns only, delegating business logic to
the `application` layer.
"""

from fastapi import APIRouter, Query
from sqlalchemy.orm import Session

from src.application.refresh import refresh_issues, refresh_pull_requests
from src.application.snapshot import create_snapshot_from_project
from src.services.db import SessionLocal

router = APIRouter(tags=["github"])


@router.post(
    "/refresh",
    summary="Rafraîchir les Issues et PRs (sans synchronisation du statut du projet)",
    response_model=None,
)
def refresh_ingest() -> None:
    """Récupère les dernières Issues et Pull Requests GitHub et les enregistre.

    Notes
    -----
    - Cette opération *ne* synchronise *pas* le statut du Project (v2) → `Task.column_name`.
    - Utilisez `/snapshot` si vous souhaitez aussi synchroniser les colonnes et enregistrer un Snapshot.
    """
    db: Session = SessionLocal()
    try:
        refresh_issues(db)
        refresh_pull_requests(db)
    finally:
        db.close()


@router.post(
    "/snapshot",
    summary=(
        "Rafraîchir Issues/PRs, synchroniser le statut Project → Task.column_name, "
        "compter par colonne et insérer un Snapshot"
    ),
)
def snapshot_projects_v2(
    number: int = Query(
        ...,
        description="Numéro du projet affiché dans l'URL (Projects v2).",
        examples=[1, 2, 42],
    ),
) -> dict:
    """Créer un snapshot Kanban à partir d'un board GitHub Projects v2.

    Étapes
    ------
    1. Rafraîchir les Issues et Pull Requests (ingester depuis GitHub).
    2. Récupérer les items du Project v2, lire le statut de chaque item, mettre à jour `Task.column_name`.
    3. Compter les tâches par colonne et persister un `Snapshot`.

    Paramètres
    ----------
    number:
        Le numéro du projet (projet user-scoped à `settings.github_owner`).

    Retourne
    --------
    dict
        Un payload du type `{"updated": <int>, "counts": {"À faire": 2, "En cours": 3, ...}}`.
    """
    db: Session = SessionLocal()
    try:
        refresh_issues(db)
        refresh_pull_requests(db)
        return create_snapshot_from_project(db, number)
    finally:
        db.close()
