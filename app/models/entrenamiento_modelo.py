"""Modelo EntrenamientoModelo (historial de entrenamientos del modelo ML)."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import Usuario


class EntrenamientoModelo(Base):
    """Registro de un entrenamiento/reentrenamiento del modelo ML."""

    __tablename__ = "entrenamientos_modelo"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estado: Mapped[str] = mapped_column(Text, nullable=False, default="pendiente")
    nombre_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    total_registros: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    version_generada: Mapped[str | None] = mapped_column(Text, nullable=True)
    metricas_nuevo: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metricas_actual: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    parametros_modelo: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tipo_mejor_modelo: Mapped[str | None] = mapped_column(Text, nullable=True)
    ruta_artefactos_candidatos: Mapped[str | None] = mapped_column(Text, nullable=True)
    mensaje_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    aceptado_por_usuario_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id"), nullable=True
    )
    fecha_decision: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    usuario: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[usuario_id])
    aceptado_por: Mapped["Usuario | None"] = relationship(
        "Usuario", foreign_keys=[aceptado_por_usuario_id]
    )
