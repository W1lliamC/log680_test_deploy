"""Modèle ORM Task.

Représente une issue GitHub localement, avec son état Kanban courant (`column_name`),
afin de calculer des métriques (lead time, WIP, complétées sur période) et alimenter
les snapshots. Mise à jour via:
- ingest REST (issues) pour created/closed/state,
- sync Projects v2 (GraphQL) pour `column_name` (Status).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.services.db import Base


class Task(Base):
    """Issue GitHub mappée au Kanban.

    Champs principaux:
    - issue_number: identifiant lisible (unique dans le repo).
    - state: "open" | "closed" (REST issues API).
    - column_name: colonne Kanban (ex. "Backlog", "À faire", "En cours", "En revue", "Terminée"),
      synchronisée depuis Projects v2 (Status) lors du snapshot/refresh.
    - created_at / closed_at: calcul du lead time.
    """

    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_state", "state"),
        Index("ix_tasks_column", "column_name"),
        Index("ix_tasks_created_at", "created_at"),
        Index("ix_tasks_closed_at", "closed_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="PK interne"
    )
    issue_number: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True,
        comment="Numéro d'issue GitHub (unique dans le repo)",
    )
    title: Mapped[str] = mapped_column(String, comment="Titre de l'issue")
    state: Mapped[str] = mapped_column(
        String, comment='État "open" ou "closed" (selon GitHub Issues)'
    )
    column_name: Mapped[str] = mapped_column(
        String,
        comment="Colonne Kanban (Status Projects v2): Backlog / À faire / En cours / En revue / Terminée",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="Date de création de l’issue"
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date de clôture de l’issue (si fermée)",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Task #{self.issue_number} [{self.state}] {self.column_name}>"
