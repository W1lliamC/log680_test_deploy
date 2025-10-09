"""Modèle ORM PullRequest.

Représente une Pull Request GitHub persistée localement pour calculer des métriques
(lead time, taux de merge, cycles de review, etc.). Ces données sont alimentées par
l’ingest (GitHub REST/GraphQL) et consommées par la couche application/metrics.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.services.db import Base


class PullRequest(Base):
    """Pull Request GitHub.

    Champs principaux:
    - pr_number: numéro de PR dans le repo (unique).
    - created_at / merged_at / closed_at: timestamps pour calculer lead time, latence, etc.
    - additions / deletions / changed_files: signal de taille/complexité.
    - reviews / commits: signal de qualité du flux de revue.
    """

    __tablename__ = "pull_requests"
    __table_args__ = (
        Index("ix_prs_created_at", "created_at"),
        Index("ix_prs_merged_at", "merged_at"),
        Index("ix_prs_closed_at", "closed_at"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="PK interne"
    )
    pr_number: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True,
        comment="Numéro de PR GitHub (unique dans le repo)",
    )
    title: Mapped[str] = mapped_column(String, comment="Titre de la PR")
    author: Mapped[str] = mapped_column(String, comment="Auteur (login GitHub)")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="Date de création de la PR"
    )
    merged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Date de merge (si merge)"
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date de fermeture (merge ou fermeture sans merge)",
    )
    head_branch: Mapped[str | None] = mapped_column(String, nullable=True)
    base_branch: Mapped[str | None] = mapped_column(String, nullable=True)
    additions: Mapped[int] = mapped_column(
        Integer, default=0, comment="Lignes ajoutées"
    )
    deletions: Mapped[int] = mapped_column(
        Integer, default=0, comment="Lignes supprimées"
    )
    changed_files: Mapped[int] = mapped_column(
        Integer, default=0, comment="Fichiers modifiés"
    )
    reviews: Mapped[int] = mapped_column(Integer, default=0, comment="Nb de reviews")
    commits: Mapped[int] = mapped_column(Integer, default=0, comment="Nb de commits")

    def __repr__(self) -> str:  # pragma: no cover (helper debug)
        return f"<PR #{self.pr_number} '{self.title}' by {self.author}>"
