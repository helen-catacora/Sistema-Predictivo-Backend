"""Esquemas para materias."""
from pydantic import BaseModel, Field


class MateriaItem(BaseModel):
    """Materia con id y nombre."""

    id: int = Field(description="ID de la materia")
    nombre: str = Field(description="Nombre de la materia (ej. Algebra (T), Fisica I (L))")


class MateriaListResponse(BaseModel):
    """Respuesta del listado de materias."""

    materias: list[MateriaItem] = Field(description="Lista de materias")
