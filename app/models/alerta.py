"""Modelo Alerta (alertas tempranas y críticas por riesgo de abandono)."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.student import Estudiante
    from app.models.prediccion import Prediccion
    from app.models.user import Usuario
    from app.models.gestion_academica import GestionAcademica


class TipoAlerta:
    """Valores permitidos para tipo de alerta."""
    TEMPRANA = "temprana"
    CRITICA = "critica"
    ABANDONO = "abandono"


class EstadoAlerta:
    """Valores permitidos para estado de alerta."""
    ACTIVA = "activa"
    EN_SEGUIMIENTO = "en_seguimiento"
    RESUELTA = "resuelta"
    DESCARTADA = "descartada"


class Alerta(Base):
    """Alerta de riesgo de abandono estudiantil."""

    __tablename__ = "alertas"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    nivel: Mapped[str] = mapped_column(Text, nullable=False)
    estudiante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("estudiantes.id"), nullable=False
    )
    prediccion_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("predicciones.id"), nullable=True
    )
    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    fecha_resolucion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estado: Mapped[str] = mapped_column(
        Text, nullable=False, default="activa", server_default=text("'activa'")
    )
    resuelta_por_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id"), nullable=True
    )
    observacion_resolucion: Mapped[str | None] = mapped_column(Text, nullable=True)
    faltas_consecutivas: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    gestion_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("gestiones_academicas.id"), nullable=True
    )

    estudiante: Mapped["Estudiante"] = relationship("Estudiante")
    prediccion: Mapped["Prediccion | None"] = relationship("Prediccion")
    resuelta_por: Mapped["Usuario | None"] = relationship("Usuario")
    gestion: Mapped["GestionAcademica | None"] = relationship("GestionAcademica")
