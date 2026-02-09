"""Modelo Estudiante."""
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.paralelo import Paralelo
    from app.models.inscripcion import Inscripcion
    from app.models.asistencia import Asistencia
    from app.models.prediccion import Prediccion


class Estudiante(Base):
    """Estudiante con código SAGA, pertenece a un paralelo."""

    __tablename__ = "estudiantes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    codigo_estudiante: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    apellido: Mapped[str] = mapped_column(Text, nullable=False)
    paralelo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("paralelos.id"), nullable=False)

    # Datos sociodemográficos (nullable para compatibilidad con registros existentes)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    genero: Mapped[str | None] = mapped_column(Text, nullable=True)
    grado: Mapped[str | None] = mapped_column(Text, nullable=True)
    estrato_socioeconomico: Mapped[str | None] = mapped_column(Text, nullable=True)  # Alto, Bajo, Medio
    ocupacion_laboral: Mapped[str | None] = mapped_column(Text, nullable=True)
    con_quien_vive: Mapped[str | None] = mapped_column(Text, nullable=True)
    apoyo_economico: Mapped[str | None] = mapped_column(Text, nullable=True)
    modalidad_ingreso: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_colegio: Mapped[str | None] = mapped_column(Text, nullable=True)

    paralelo: Mapped["Paralelo"] = relationship("Paralelo", back_populates="estudiantes")
    inscripciones: Mapped[list["Inscripcion"]] = relationship(
        "Inscripcion", back_populates="estudiante"
    )
    asistencias: Mapped[list["Asistencia"]] = relationship(
        "Asistencia", back_populates="estudiante"
    )
    predicciones: Mapped[list["Prediccion"]] = relationship(
        "Prediccion", back_populates="estudiante"
    )
