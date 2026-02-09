"""Esquemas para alertas de riesgo de abandono."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


ESTADOS_ALERTA = ["activa", "en_seguimiento", "resuelta", "descartada"]


class AlertaItem(BaseModel):
    """Fila de la lista de alertas."""
    id: int
    tipo: str
    nivel: str
    estudiante_id: int
    nombre_estudiante: str
    codigo_estudiante: str
    paralelo: str
    titulo: str
    descripcion: str
    fecha_creacion: datetime
    estado: str
    faltas_consecutivas: int


class AlertasListResponse(BaseModel):
    """Respuesta de la lista de alertas."""
    total: int
    total_activas: int
    total_criticas: int
    alertas: list[AlertaItem]


class AlertaUpdateRequest(BaseModel):
    """Request para actualizar el estado de una alerta."""
    estado: str = Field(description="Nuevo estado: en_seguimiento, resuelta o descartada")
    observacion_resolucion: str | None = Field(
        default=None, description="Comentario al resolver/descartar"
    )

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: str) -> str:
        if v not in ESTADOS_ALERTA:
            raise ValueError(f"estado debe ser uno de: {', '.join(ESTADOS_ALERTA)}")
        return v


class AlertaUpdateResponse(BaseModel):
    """Respuesta al actualizar una alerta."""
    id: int
    estado: str
    resuelta_por: str | None = None
    fecha_resolucion: datetime | None = None
    observacion_resolucion: str | None = None
