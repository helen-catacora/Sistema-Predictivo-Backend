"""Modelo Inscripción (matriz Excel: estudiante–materia–gestión)."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Identity, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.student import Estudiante
    from app.models.subject import Materia


class Inscripcion(Base):
    """Inscripción: estudiante inscrito en materia en una gestión académica (ej. I-2026)."""

    __tablename__ = "inscripciones"
    __table_args__ = (
        UniqueConstraint(
            "estudiante_id", "materia_id", "gestion_academica",
            name="uq_inscripciones_estudiante_materia_gestion"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    estudiante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("estudiantes.id"), nullable=False
    )
    materia_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("materias.id"), nullable=False
    )
    gestion_academica: Mapped[str] = mapped_column(Text, nullable=False)

    estudiante: Mapped["Estudiante"] = relationship("Estudiante", back_populates="inscripciones")
    materia: Mapped["Materia"] = relationship("Materia", back_populates="inscripciones")
