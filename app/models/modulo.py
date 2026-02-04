"""Modelo Módulo y asociación usuario-módulo (restricción de acceso por usuario)."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import Usuario


class Modulo(Base):
    """Módulo del sistema al que se puede restringir el acceso (ej. asistencias, estudiantes, reportes)."""

    __tablename__ = "modulos"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    usuarios: Mapped[list["Usuario"]] = relationship(
        "Usuario",
        secondary="usuario_modulo",
        back_populates="modulos",
    )


class UsuarioModulo(Base):
    """Tabla asociación: qué módulos puede acceder cada usuario (restricción por usuario)."""

    __tablename__ = "usuario_modulo"

    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    modulo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("modulos.id", ondelete="CASCADE"), primary_key=True
    )
