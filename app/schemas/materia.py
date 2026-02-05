"""Esquemas para materias (desde malla curricular)."""
from pydantic import BaseModel, Field


class MateriaItem(BaseModel):
    """Materia en la malla curricular: id, nombre, area_id y semestre_id."""

    id: int = Field(description="ID de la materia")
    nombre: str = Field(description="Nombre de la materia")
    area_id: int | None = Field(default=None, description="ID del área en la malla")
    semestre_id: int | None = Field(default=None, description="ID del semestre en la malla")


class MateriaListResponse(BaseModel):
    """Respuesta del listado de materias (desde malla_curricular)."""

    materias: list[MateriaItem] = Field(description="Lista de materias en la malla curricular")
