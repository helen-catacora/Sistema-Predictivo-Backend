"""Modelo ReporteGenerado — registro de reportes PDF generados."""
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import Usuario


class ReporteGenerado(Base):
    """Registro de cada reporte PDF generado (solo metadatos, sin el archivo)."""

    __tablename__ = "reportes_generados"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    generado_por_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id"), nullable=False
    )
    fecha_generacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    parametros: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    generado_por: Mapped["Usuario"] = relationship("Usuario")
