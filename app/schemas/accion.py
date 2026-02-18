"""Esquemas para acciones de seguimiento de predicciones."""
from datetime import date

from pydantic import BaseModel, Field


class AccionCreateRequest(BaseModel):
    """Request para crear una acción de seguimiento."""

    descripcion: str = Field(
        description="Descripción de la acción tomada (ej. 'Entrevista con psicopedagogía')",
        min_length=1,
        max_length=2000,
    )
    fecha: date = Field(
        description="Fecha en que se realizó la acción (formato: YYYY-MM-DD)",
    )
    estudiante_id: int = Field(
        description="ID del estudiante sobre el cual se tomó la acción",
        gt=0,
    )


class AccionCreateResponse(BaseModel):
    """Respuesta al crear una acción."""

    id: int = Field(description="ID de la acción creada")
    descripcion: str = Field(description="Descripción de la acción")
    fecha: date = Field(description="Fecha de la acción")
    prediccion_id: int = Field(description="ID de la predicción asociada")
    estudiante_id: int = Field(description="ID del estudiante asociado a la predicción")
    estudiante_nombre: str = Field(description="Nombre completo del estudiante")


class AccionListItem(BaseModel):
    """Item de acción para listados."""

    id: int
    descripcion: str
    fecha: date
    prediccion_id: int
    estudiante_id: int
    estudiante_nombre: str
    fecha_prediccion: date
    nivel_riesgo: str


class AccionListResponse(BaseModel):
    """Respuesta del listado de acciones."""

    total: int = Field(description="Total de acciones")
    acciones: list[AccionListItem] = Field(description="Lista de acciones")
