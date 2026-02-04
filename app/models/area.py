"""Modelo Área (estructura académica)."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Identity, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.paralelo import Paralelo
    from app.models.malla_curricular import MallaCurricular


class Area(Base):
    """Área: Tecnológicas, No Tecnológicas, etc."""

    __tablename__ = "areas"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    paralelos: Mapped[list["Paralelo"]] = relationship("Paralelo", back_populates="area")
    mallas: Mapped[list["MallaCurricular"]] = relationship(
        "MallaCurricular", back_populates="area"
    )
