from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import Session

from src.application.schemas import PRBranches, PRCount, PRLeadTimeItem, PRStats
from src.database.pull_request import PullRequest
from src.services.db import SessionLocal

router = APIRouter(prefix="/metrics/prs", tags=["pull-requests"])


@router.get(
    "/lead-time/{pr_number}",
    response_model=PRLeadTimeItem,
    response_model_exclude_none=True,
    summary="Retourne le lead time d'une pull request (en jours) et, si elle est ouverte, son âge.",
    description=(
        "Définition:\n"
        "- Lead time = `closed_at - created_at` **uniquement si** l'issue est fermée.\n"
        "- Pour une PR ouverte, `lead_time` est `None` et `age = now - created_at`.\n\n"
        "Remarques:\n"
        "- Cette route ne modifie pas la base; elle lit uniquement les champs existants."
        "- Si aucune PR ne correspond au pr_number entrant, une exception à retournée"
    ),
)
def get_pr_lead_time(pr_number: int) -> PRLeadTimeItem:
    db: Session = SessionLocal()
    try:
        row = db.query(PullRequest).filter_by(pr_number=pr_number).one_or_none()
        if not row:
            raise HTTPException(
                status_code=404, detail=f"Non existent PR for number: {pr_number}"
            )
        return PRLeadTimeItem.from_pr(row)
    finally:
        db.close()


@router.get(
    "/lead-time",
    response_model=List[PRLeadTimeItem],
    response_model_exclude_none=True,
    summary="Liste des lead times pour les PR fermées dans une période donnée",
    description=(
        "Définition:\n"
        " - Filtrage sur `state='closed'` ET `closed_at` non nul.\n"
        " - `lead_time` = (merged_at/closed_at - created_at) en **jours** (float).\n"
        " - `age` n’est pas renseigné ici (toujours `None`) car on ne renvoie que des PR fermées.\n"
        " - Si `start`/`end` ne sont pas fournis, on renvoie toutes les PR fermées.\n"
    ),
)
def list_pr_lead_times(
    start: Optional[datetime] = Query(
        None,
        description="Inclure PRs terminées (merged/closed) à partir de cette date (UTC) — filtre sur merged_at/closed_at >= start",
    ),
    end: Optional[datetime] = Query(
        None,
        description="Inclure PRs terminées (merged/closed) jusqu’à cette date (UTC) — filtre sur merged_at/closed_at <= end",
    ),
) -> List[PRLeadTimeItem]:
    db: Session = SessionLocal()
    try:
        q = db.query(PullRequest).filter(
            (PullRequest.merged_at.isnot(None)) | (PullRequest.closed_at.isnot(None))
        )
        if start:
            q = q.filter(
                (PullRequest.merged_at >= start) | (PullRequest.closed_at >= start)
            )
        if end:
            q = q.filter(
                (PullRequest.merged_at <= end) | (PullRequest.closed_at <= end)
            )

        q = q.order_by(
            PullRequest.merged_at.asc().nulls_last(),
            PullRequest.closed_at.asc().nulls_last(),
        )
        rows = q.all()
        items = [PRLeadTimeItem.from_pr(r) for r in rows]
        return items
    finally:
        db.close()


@router.get(
    "/commits/{pr_number}",
    response_model=PRCount,
    response_model_exclude_none=True,
    summary="Retourne le **nombre de commits** pour une PR donnée.",
    description=(
        "Renvoie le nombre de commits pour une PR donnée.\n\n"
        "**Note:** Si aucune PR ne correspond au pr_number entrant, une exception à retournée"
    ),
)
@router.get("/commits/{pr_number}")
def get_pr_commits_count(pr_number: int) -> PRCount:
    db: Session = SessionLocal()
    try:
        row = db.query(PullRequest).filter_by(pr_number=pr_number).one_or_none()
        if not row:
            raise HTTPException(
                status_code=404, detail=f"Non existent PR for number: {pr_number}"
            )
        return PRCount(pr_number=row.pr_number, title=row.title, count=row.commits)
    finally:
        db.close()


@router.get(
    "/reviews/{pr_number}",
    response_model=PRCount,
    response_model_exclude_none=True,
    summary="Retourne le **nombre de reviews** pour une PR donnée.",
    description=(
        "Renvoie le nombre de reviews pour une PR donnée.\n\n"
        "**Note:** Si aucune PR ne correspond au pr_number entrant, une exception à retournée"
    ),
)
def get_pr_reviews_count(pr_number: int) -> PRCount:
    db: Session = SessionLocal()
    try:
        row = db.query(PullRequest).filter_by(pr_number=pr_number).one_or_none()
        if not row:
            raise HTTPException(
                status_code=404, detail=f"Non existent PR for number: {pr_number}"
            )
        return PRCount(pr_number=row.pr_number, title=row.title, count=row.reviews)
    finally:
        db.close()


# ---- 5) Stats additions/deletions/changed_files (agrégé) ---------------------


@router.get(
    "/stats/{pr_number}",
    response_model=PRStats,
    response_model_exclude_none=True,
    summary="Retourne les **statistiques** pour une PR donnée.",
    description=(
        "Renvoie les statistiques pour une PR donnée. Ceci inclut:\n"
        "- `additions` qui est le nombre de lignes ajoutées par la PR\n"
        "- `deletions` qui est le nombre de lignes enlevées par la PR\n"
        "- `changed_files` qui est le nombre de fichiers modifés par la PR\n\n"
        "**Note:** Si aucune PR ne correspond au pr_number entrant, une exception à retournée"
    ),
)
def get_pr_stats(pr_number: int) -> PRStats:
    db: Session = SessionLocal()
    try:
        row = db.query(PullRequest).filter_by(pr_number=pr_number).one_or_none()
        if not row:
            raise HTTPException(
                status_code=404, detail=f"Non existent PR for number: {pr_number}"
            )
        return PRStats(
            pr_number=row.pr_number,
            title=row.title,
            additions=row.additions,
            deletions=row.deletions,
            changed_files=row.changed_files,
        )
    finally:
        db.close()


@router.get(
    "/branches/{pr_number}",
    response_model=PRBranches,
    response_model_exclude_none=True,
    summary="Retourne les **branches** pour une PR donnée.",
    description=(
        "Renvoie les branches pour une PR donnée. Ceci inclut:\n"
        "- `head` qui est la branche de provenance de la PR\n"
        "- `base` qui est le branche dans laquelle la PR à été merger\n"
        "**Note:** Si aucune PR ne correspond au pr_number entrant, une exception à retournée"
    ),
)
def get_pr_branches(pr_number: int) -> PRBranches:
    db: Session = SessionLocal()
    try:
        row = db.query(PullRequest).filter_by(pr_number=pr_number).one_or_none()
        if not row:
            raise HTTPException(
                status_code=404, detail=f"Non existent PR for number: {pr_number}"
            )
        return PRBranches(
            pr_number=row.pr_number,
            title=row.title,
            head=row.head_branch,
            base=row.base_branch,
        )
    finally:
        db.close()
