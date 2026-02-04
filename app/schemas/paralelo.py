"""Esquemas para paralelos."""
from pydantic import BaseModel, Field


class ParaleloItem(BaseModel):
    """Paralelo con id, nombre y nombre del encargado."""

    id: int = Field(description="ID del paralelo")
    nombre: str = Field(description="Nombre del paralelo (ej. 1-A, 1-B)")
    nombre_encargado: str = Field(description="Nombre del usuario encargado del paralelo")


class ParaleloListResponse(BaseModel):
    """Respuesta del listado de paralelos."""

    paralelos: list[ParaleloItem] = Field(description="Lista de paralelos")
