"""Modelo LotePrediccion (agrupación de predicciones por carga Excel)."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import Usuario
    from app.models.gestion_academica import GestionAcademica
    from app.models.prediccion import Prediccion


class EstadoLote:
    """Valores permitidos para estado del lote."""
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"
    COMPLETADO = "completado"
    ERROR = "error"


class LotePrediccion(Base):
    """Lote de predicciones generadas a partir de una carga masiva de Excel."""

    __tablename__ = "lotes_prediccion"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_carga: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id"), nullable=False
    )
    gestion_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("gestiones_academicas.id"), nullable=True
    )
    estado: Mapped[str] = mapped_column(
        Text, nullable=False, default="pendiente", server_default=text("'pendiente'")
    )
    total_estudiantes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_procesados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_alto_riesgo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_medio_riesgo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bajo_riesgo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_critico: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mensaje_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_modelo: Mapped[str] = mapped_column(
        Text, nullable=False, default="v2_con_imputacion_knn"
    )

    usuario: Mapped["Usuario"] = relationship("Usuario")
    gestion: Mapped["GestionAcademica | None"] = relationship("GestionAcademica")
    predicciones: Mapped[list["Prediccion"]] = relationship(
        "Prediccion", back_populates="lote"
    )
