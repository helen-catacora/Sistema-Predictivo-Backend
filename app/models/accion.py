"""Modelo Acción (seguimiento de una predicción)."""
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.prediccion import Prediccion


class Accion(Base):
    """Acción tomada a partir de una predicción (ej. entrevista con psicopedagogía)."""

    __tablename__ = "acciones"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    prediccion_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("predicciones.id"), nullable=False
    )

    prediccion: Mapped["Prediccion"] = relationship("Prediccion", back_populates="acciones")
