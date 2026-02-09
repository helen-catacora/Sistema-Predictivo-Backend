"""Esquemas para gestiones académicas."""
from datetime import date

from pydantic import BaseModel, Field


class GestionAcademicaCreate(BaseModel):
    """Request para crear una gestión académica."""
    nombre: str = Field(description="Nombre de la gestión (ej. I-2026)")
    fecha_inicio: date = Field(description="Fecha de inicio del período")
    fecha_fin: date = Field(description="Fecha de fin del período")


class GestionAcademicaItem(BaseModel):
    """Fila de la lista de gestiones."""
    id: int
    nombre: str
    fecha_inicio: date
    fecha_fin: date
    activa: bool


class GestionAcademicaListResponse(BaseModel):
    """Lista de gestiones académicas."""
    gestiones: list[GestionAcademicaItem]
