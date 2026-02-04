"""Modelo Semestre (estructura académica)."""
from sqlalchemy import BigInteger, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Semestre(Base):
    """Semestre académico: Primer Semestre, Segundo Semestre, etc."""

    __tablename__ = "semestres"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    mallas: Mapped[list["MallaCurricular"]] = relationship(
        "MallaCurricular", back_populates="semestre"
    )
