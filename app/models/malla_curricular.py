"""Modelo Malla Curricular (materia por área y semestre)."""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Identity, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.subject import Materia
    from app.models.area import Area
    from app.models.semester import Semestre


class MallaCurricular(Base):
    """Relación materia–área–semestre en la malla curricular."""

    __tablename__ = "malla_curricular"
    __table_args__ = (
        UniqueConstraint(
            "materia_id", "area_id", "semestre_id",
            name="uq_malla_curricular_materia_area_semestre"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    materia_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("materias.id"), nullable=True
    )
    area_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("areas.id"), nullable=True
    )
    semestre_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("semestres.id"), nullable=True
    )

    materia: Mapped["Materia"] = relationship("Materia", back_populates="mallas")
    area: Mapped["Area"] = relationship("Area", back_populates="mallas")
    semestre: Mapped["Semestre"] = relationship("Semestre", back_populates="mallas")
