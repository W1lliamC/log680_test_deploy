"""Modèle ORM Snapshot.

Capture ponctuelle de l'état du Kanban (ex. distribution par colonne).
Utilisé pour historiser et répondre à des questions temporelles (goulot d'étranglement,
état à une date donnée, moyennes sur une période, etc.).
"""

from __future__ import annotations

from datetime import datetime

# Astuce: si PostgreSQL, JSONB est plus efficace pour l'indexation et les opérateurs.
# from sqlalchemy.dialects.postgresql import JSONB as JSONType
from sqlalchemy import JSON as JSONType  # portable (fonctionne sur SQLite également)
from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.services.db import Base


class Snapshot(Base):
    """Snapshot Kanban.

    - ts: horodatage de la capture.
    - counts: dict { "À faire": 2, "En cours": 3, "Terminée": 7, ... }.
      En PostgreSQL, préférez JSONB si vous prévoyez d’indexer/filtrer sur ce contenu.
    """

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="PK interne"
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        comment="Horodatage de la capture (UTC)",
    )
    counts: Mapped[dict] = mapped_column(
        JSONType, comment="Distribution par colonne: {'À faire': 2, 'En cours': 3, ...}"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Snapshot {self.id} @ {self.ts.isoformat()}>"
