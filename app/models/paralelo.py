"""Modelo Paralelo (grupo por área con encargado)."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Identity, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.area import Area
    from app.models.user import Usuario
    from app.models.student import Estudiante


class Paralelo(Base):
    """Paralelo: ej. 1-A, 1-B; pertenece a un área y tiene un encargado."""

    __tablename__ = "paralelos"
    __table_args__ = (UniqueConstraint("nombre", "area_id", name="uq_paralelos_nombre_area_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    area_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("areas.id"), nullable=False)
    encargado_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)

    area: Mapped["Area"] = relationship("Area", back_populates="paralelos")
    encargado: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="paralelos_encargado", foreign_keys=[encargado_id]
    )
    estudiantes: Mapped[list["Estudiante"]] = relationship(
        "Estudiante", back_populates="paralelo"
    )
