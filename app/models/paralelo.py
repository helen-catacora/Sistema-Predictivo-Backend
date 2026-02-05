"""Modelo Paralelo (grupo por área y semestre con encargado)."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Identity, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.area import Area
    from app.models.semester import Semestre
    from app.models.user import Usuario
    from app.models.student import Estudiante


class Paralelo(Base):
    """Paralelo: ej. 1-A, 1-B; pertenece a un área, un semestre y tiene un encargado."""

    __tablename__ = "paralelos"
    __table_args__ = (UniqueConstraint("nombre", "area_id", name="uq_paralelos_nombre_area_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    area_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("areas.id"), nullable=False)
    semestre_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("semestres.id"), nullable=True
    )
    encargado_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)

    area: Mapped["Area"] = relationship("Area", back_populates="paralelos")
    semestre: Mapped["Semestre | None"] = relationship(
        "Semestre", back_populates="paralelos", foreign_keys=[semestre_id]
    )
    encargado: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="paralelos_encargado", foreign_keys=[encargado_id]
    )
    estudiantes: Mapped[list["Estudiante"]] = relationship(
        "Estudiante", back_populates="paralelo"
    )
