from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.application.schemas import KanbanCount, KanbanLeadTimeItem
from src.database.task import Task
from src.services.db import SessionLocal

router = APIRouter(prefix="/metrics/kanban", tags=["kanban"])


@router.get(
    "/lead-time/{issue_number}",
    response_model=KanbanLeadTimeItem,
    response_model_exclude_none=True,
    summary="Retourne le lead time d'une issue (en jours) et, si elle est ouverte, son âge.",
    description=(
        "Définition:\n"
        "- Lead time = `closed_at - created_at` **uniquement si** l'issue est fermée.\n"
        "- Pour une issue ouverte, `lead_time` est `None` et `age = now - created_at`.\n\n"
        "Remarques:\n"
        "- Cette route ne modifie pas la base; elle lit uniquement les champs existants."
        "- Si aucune issue ne correspond au issue_number entrant, une exception à retournée"
    ),
)
def get_issue_lead_time(issue_number: int) -> KanbanLeadTimeItem:
    db: Session = SessionLocal()
    try:
        row = db.query(Task).filter_by(issue_number=issue_number).one_or_none()
        if not row:
            raise HTTPException(
                status_code=404, detail=f"Non existent issue_number for number: {issue_number}"
            )
        return KanbanLeadTimeItem.from_task(row)
    finally:
        db.close()


@router.get(
    "/lead-time",
    response_model=List[KanbanLeadTimeItem],
    response_model_exclude_none=True,
    summary="Liste des lead times pour les issues fermées dans une période donnée",
    description=(
        "Définition:\n"
        " - Filtrage sur `state='closed'` ET `closed_at` non nul.\n"
        " - `lead_time` = (closed_at - created_at) en **jours** (float).\n"
        " - `age` n’est pas renseigné ici (toujours `None`) car on ne renvoie que des issues fermées.\n"
        " - Si `start`/`end` ne sont pas fournis, on renvoie toutes les issues fermées.\n"
    ),
)
def list_issue_lead_times(
    start: Optional[datetime] = Query(
        None,
        description="Inclure issues fermées à partir de cette date (UTC), filtrage sur closed_at >= start",
    ),
    end: Optional[datetime] = Query(
        None,
        description="Inclure issues fermées jusqu’à cette date (UTC), filtrage sur closed_at <= end",
    ),
) -> list[KanbanLeadTimeItem]:
    db: Session = SessionLocal()
    try:
        q = db.query(Task).filter(Task.state == "closed", Task.closed_at.isnot(None))
        if start:
            q = q.filter(Task.closed_at >= start)
        if end:
            q = q.filter(Task.closed_at <= end)

        q = q.order_by(Task.closed_at.asc())
        rows = q.all()

        items = [KanbanLeadTimeItem.from_task(r) for r in rows]
        return items
    finally:
        db.close()


@router.get(
    "/active-count",
    response_model=KanbanCount | List[KanbanCount],
    response_model_exclude_none=True,
    summary="Nombre de tâches actives pour une colonne donnée",
    description=(
        "Renvoie le nombre de tâches actives (issues non fermées) pour une colonne Kanban donnée.\n"
        "- Filtrage sur `column_name` (nom exact de la colonne, ex: 'Backlog', 'En cours', etc.).\n"
        "- Si le champ `column_name` n'est pas inclut, retourne une liste de des colonnes avec des issues actives et leur nombre\n"
        "- Seules les issues actives, donc qui ont `state != 'closed'`, sont comptées.\n"
        "- Le champ `count` du résultat est de 0 s'il n'y a aucune issue ou si la colonne n'existe pas."
    ),
)
def active_count(
    column: Optional[str] = Query(
        None,
        description="ex: 'En cours'. Si omis, retourne le nombre d'issues actives pour chaque colonne qui ont des issues actifs.",
    )
):
    db: Session = SessionLocal()
    try:
        if column is not None:
            n = (
                db.query(Task)
                .filter(Task.column_name == column, Task.state != "closed")
                .count()
            )
            return KanbanCount(column=column, count=n)
        else:
            # Retourne une liste de toutes les colonnes avec leur nombre d'issues actives
            results = (
                db.query(Task.column_name, func.count().label("count"))
                .filter(Task.state != "closed")
                .group_by(Task.column_name)
                .all()
            )
            # Si aucune issue active, retourne une liste vide
            return [KanbanCount(column=col, count=count) for col, count in results]
    finally:
        db.close()


@router.get(
    "/completed-count",
    response_model=int,
    response_model_exclude_none=True,
    summary="Nombre de tâches complétées pour une période",
    description=(
        "Définition:\n"
        " - Filtrage sur `state='closed'` ET `closed_at` non nul.\n"
        " - Si `start`/`end` ne sont pas fournis, on renvoie le nombre total des issues fermées.\n"
    ),
)
def completed_count(
    start: Optional[datetime] = Query(
        None,
        description="Inclure issues fermées à partir de cette date (UTC), filtrage sur closed_at >= start",
    ),
    end: Optional[datetime] = Query(
        None,
        description="Inclure issues fermées jusqu’à cette date (UTC), filtrage sur closed_at <= end",
    ),
):
    db: Session = SessionLocal()
    try:
        q = db.query(Task).filter(Task.state == "closed", Task.closed_at.isnot(None))
        if start:
            q = q.filter(Task.closed_at >= start)
        if end:
            q = q.filter(Task.closed_at <= end)

        q = q.order_by(Task.closed_at.asc())
        rows = q.all()

        return len(rows)
    finally:
        db.close()
