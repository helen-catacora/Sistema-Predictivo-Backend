"""Modelo Rol (RBAC)."""
from sqlalchemy import BigInteger, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Rol(Base):
    """Rol del usuario: Administrador, Encargado, etc."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    usuarios: Mapped[list["Usuario"]] = relationship("Usuario", back_populates="rol")
