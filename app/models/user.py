"""Modelo Usuario (RBAC)."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Identity, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.role import Rol
    from app.models.paralelo import Paralelo
    from app.models.asistencia import Asistencia
    from app.models.modulo import Modulo


class Usuario(Base):
    """Usuario del sistema (encargados, administradores)."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    rol_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("roles.id"), nullable=False)
    estado: Mapped[str] = mapped_column(
        Text, nullable=False, default="activo", server_default=text("'activo'")
    )
    carnet_identidad: Mapped[str | None] = mapped_column(Text, nullable=True)
    telefono: Mapped[str | None] = mapped_column(Text, nullable=True)
    cargo: Mapped[str | None] = mapped_column(Text, nullable=True)

    rol: Mapped["Rol"] = relationship("Rol", back_populates="usuarios")
    paralelos_encargado: Mapped[list["Paralelo"]] = relationship(
        "Paralelo", back_populates="encargado", foreign_keys="Paralelo.encargado_id"
    )
    asistencias_registradas: Mapped[list["Asistencia"]] = relationship(
        "Asistencia", back_populates="encargado"
    )
    modulos: Mapped[list["Modulo"]] = relationship(
        "Modulo", secondary="usuario_modulo", back_populates="usuarios"
    )
