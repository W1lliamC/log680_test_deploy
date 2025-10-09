# src/domain/schemas.py
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.database.pull_request import PullRequest
from src.database.task import Task


class KanbanLeadTimeItem(BaseModel):
    """Lead time pour une issue unique."""

    issue_number: int = Field(..., description="Numéro de l'issue GitHub")
    title: str = Field(None, description="Titre de l'issue ou null")
    state: Literal["open", "closed"] = Field(..., description="État de l'issue")
    created_at: datetime = Field(..., description="Date de création (ISO8601)")
    closed_at: Optional[datetime] = Field(
        None, description="Date de fermeture (ISO8601) ou null si ouverte"
    )
    lead_time: Optional[float] = Field(
        None, description="Lead time en jours (float) si fermée, sinon null"
    )
    age: Optional[float] = Field(
        None, description="Âge en jours (float) si ouverte, sinon null"
    )
    column_name: Optional[str] = Field(
        None, description="Nom de la colonne Kanban ou null"
    )

    @classmethod
    def from_task(
        cls,
        task: Task,
        *,
        include_age_for_open: bool = True,
    ) -> "KanbanLeadTimeItem":
        """Construire un `KanbanLeadTimeItem` à partir d'un objet ORM `Task`.

        Args:
            task: Instance SQLAlchemy `Task`.
            include_age_for_open: Si True, calcule `age` pour les issues ouvertes.

        Returns:
            KanbanLeadTimeItem: modèle Pydantic prêt à sérialiser.
        """
        now = datetime.now(timezone.utc)
        sec_per_day = 86400.0

        lead_days: Optional[float] = None
        age_days: Optional[float] = None

        if task.state == "closed" and task.closed_at:
            lead_days = (task.closed_at - task.created_at).total_seconds() / sec_per_day
        elif include_age_for_open:
            age_days = (now - task.created_at).total_seconds() / sec_per_day

        return cls(
            issue_number=task.issue_number,
            state=task.state,
            created_at=task.created_at,
            closed_at=task.closed_at,
            lead_time=lead_days,
            age=age_days,
            column_name=getattr(task, "column_name", None),
        )


class KanbanCount(BaseModel):
    """Comptage pour une colonne."""

    column: str = Field(None, description="Nom de la colonne demandée")
    count: int = Field(
        ...,
        description="Compte du nombre d'issue pour la colonne `column`. 0 si aucune issue ou si colonne n'existe pas.",
    )


class PRLeadTimeItem(BaseModel):
    """Lead time d'une PR = merged_at/closed_at - created_at (si fermée/mergée)."""

    pr_number: int = Field(..., description="Numéro de la PR GitHub")
    title: str = Field(None, description="Titre de la PR ou null")
    created_at: datetime = Field(..., description="Date de création (ISO8601)")
    merged_at: Optional[datetime] = Field(
        None, description="Date de merge (ISO8601) ou null si ouverte"
    )
    closed_at: Optional[datetime] = Field(
        None, description="Date de fermeture (ISO8601) ou null si ouverte"
    )
    lead_time: Optional[float] = Field(
        None, description="Lead time en jours (float) si fermée, sinon null"
    )
    age: Optional[float] = Field(
        None, description="Âge en jours (float) si ouverte, sinon null"
    )

    @classmethod
    def from_pr(
        cls,
        pr: PullRequest,
        *,
        include_age_for_open: bool = True,
    ) -> "PRLeadTimeItem":
        """Construire un `PRLeadTimeItem` à partir d'un objet ORM `PullRequest`.

        Args:
            pr: Instance SQLAlchemy `PullRequest`.
            include_age_for_open: Si True, calcule `age` pour les issues ouvertes.

        Returns:
            KanbanLeadTimeItem: modèle Pydantic prêt à sérialiser.
        """
        now = datetime.now(timezone.utc)
        sec_per_day = 86400.0

        lead_days: Optional[float] = None
        age_days: Optional[float] = None

        if pr.closed_at:
            lead_days = (pr.closed_at - pr.created_at).total_seconds() / sec_per_day
        elif pr.merged_at:
            lead_days = (pr.merged_at - pr.created_at).total_seconds() / sec_per_day
        elif include_age_for_open:
            age_days = (now - pr.created_at).total_seconds() / sec_per_day

        return cls(
            pr_number=pr.pr_number,
            created_at=pr.created_at,
            merged_at=pr.merged_at,
            closed_at=pr.closed_at,
            lead_time=lead_days,
            age=age_days,
        )


class PRCount(BaseModel):
    """Nombre de commits ou reviews pour une PR donnée"""

    pr_number: int = Field(..., description="Numéro de la PR GitHub")
    title: str = Field(None, description="Titre de la PR ou null")
    count: int = Field(..., description="Nombre de commits ou reviews pour la PR")


class PRStats(BaseModel):
    """Statistiques liées à une PR"""

    pr_number: int = Field(..., description="Numéro de la PR GitHub")
    title: str = Field(None, description="Titre de la PR ou null")
    additions: int = Field(..., description="Lignes ajoutées")
    deletions: int = Field(..., description="Lignes supprimées")
    changed_files: int = Field(..., description="Fichiers modifiés")


class PRBranches(BaseModel):
    """Branche head et base pour une PR donnée"""

    pr_number: int = Field(..., description="Numéro de la PR GitHub")
    title: str = Field(None, description="Titre de la PR ou null")
    head: str = Field(None, description="Branche de provenance de la PR")
    base: str = Field(..., description="Branche dans laquelle la PR à été merger")
