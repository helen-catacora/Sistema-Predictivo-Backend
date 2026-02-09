"""Modelo Predicción (resultado del modelo ML de abandono)."""
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, Double, ForeignKey, Identity, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.student import Estudiante
    from app.models.accion import Accion
    from app.models.lote_prediccion import LotePrediccion
    from app.models.gestion_academica import GestionAcademica


class NivelRiesgo:
    """Valores permitidos para nivel de riesgo."""
    BAJO = "Bajo"
    MEDIO = "Medio"
    ALTO = "Alto"
    CRITICO = "Critico"


class Prediccion(Base):
    """Predicción de abandono por estudiante (XGBoost)."""

    __tablename__ = "predicciones"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    probabilidad_abandono: Mapped[float] = mapped_column(Double, nullable=False)
    nivel_riesgo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_prediccion: Mapped[date] = mapped_column(Date, nullable=False)
    estudiante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("estudiantes.id"), nullable=False
    )
    lote_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("lotes_prediccion.id"), nullable=True
    )
    gestion_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("gestiones_academicas.id"), nullable=True
    )
    tipo: Mapped[str] = mapped_column(
        Text, nullable=False, default="masiva", server_default=text("'masiva'")
    )
    features_utilizadas: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version_modelo: Mapped[str | None] = mapped_column(Text, nullable=True)

    estudiante: Mapped["Estudiante"] = relationship("Estudiante", back_populates="predicciones")
    acciones: Mapped[list["Accion"]] = relationship("Accion", back_populates="prediccion")
    lote: Mapped["LotePrediccion | None"] = relationship(
        "LotePrediccion", back_populates="predicciones"
    )
    gestion: Mapped["GestionAcademica | None"] = relationship("GestionAcademica")
