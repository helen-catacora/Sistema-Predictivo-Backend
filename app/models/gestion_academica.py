"""Modelo GestionAcademica (período académico: I-2026, II-2025, etc.)."""
from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, Identity, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GestionAcademica(Base):
    """Período académico con fecha de inicio/fin y estado activo."""

    __tablename__ = "gestiones_academicas"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    activa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
