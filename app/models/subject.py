"""Modelo Materia."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.malla_curricular import MallaCurricular
    from app.models.inscripcion import Inscripcion
    from app.models.asistencia import Asistencia


class Materia(Base):
    """Materia: ej. Algebra (T), Física I (L)."""

    __tablename__ = "materias"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    mallas: Mapped[list["MallaCurricular"]] = relationship(
        "MallaCurricular", back_populates="materia"
    )
    inscripciones: Mapped[list["Inscripcion"]] = relationship(
        "Inscripcion", back_populates="materia"
    )
    asistencias: Mapped[list["Asistencia"]] = relationship(
        "Asistencia", back_populates="materia"
    )
