"""Modelo Predicción (resultado del modelo Random Forest)."""
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, Double, ForeignKey, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.student import Estudiante
    from app.models.accion import Accion


class NivelRiesgo:
    """Valores permitidos para nivel de riesgo."""
    BAJO = "Bajo"
    MEDIO = "Medio"
    ALTO = "Alto"
    CRITICO = "Critico"


class Prediccion(Base):
    """Predicción de abandono por estudiante (Random Forest)."""

    __tablename__ = "predicciones"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    probabilidad_abandono: Mapped[float] = mapped_column(Double, nullable=False)
    nivel_riesgo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_prediccion: Mapped[date] = mapped_column(Date, nullable=False)
    estudiante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("estudiantes.id"), nullable=False
    )

    estudiante: Mapped["Estudiante"] = relationship("Estudiante", back_populates="predicciones")
    acciones: Mapped[list["Accion"]] = relationship("Accion", back_populates="prediccion")
