"""Modelo LoteImportacionEstudiante (registro de cada carga Excel de creación de estudiantes)."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import Usuario


class LoteImportacionEstudiante(Base):
    """Registro de cada archivo Excel subido para la creación/actualización de estudiantes."""

    __tablename__ = "lotes_importacion_estudiantes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre_archivo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_carga: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id"), nullable=False
    )
    total_filas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estudiantes_creados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estudiantes_actualizados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_errores: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    usuario: Mapped["Usuario"] = relationship("Usuario")
