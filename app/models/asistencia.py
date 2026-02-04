"""Modelo Asistencia (registro diario por estudiante/materia)."""
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.student import Estudiante
    from app.models.subject import Materia
    from app.models.user import Usuario


class EstadoAsistencia:
    """Valores permitidos para estado de asistencia."""
    PRESENTE = "Presente"
    AUSENTE = "Ausente"
    JUSTIFICADO = "Justificado"
    NO_CURSA = "No Cursa"


class Asistencia(Base):
    """Asistencia: presente/ausente/justificado/no cursa por fecha, estudiante y materia."""

    __tablename__ = "asistencias"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(Text, nullable=False)
    observacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estudiante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("estudiantes.id"), nullable=False
    )
    materia_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("materias.id"), nullable=False
    )
    encargado_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id"), nullable=False
    )

    estudiante: Mapped["Estudiante"] = relationship("Estudiante", back_populates="asistencias")
    materia: Mapped["Materia"] = relationship("Materia", back_populates="asistencias")
    encargado: Mapped["Usuario"] = relationship("Usuario", back_populates="asistencias_registradas")
