"""Esquemas para generación de reportes PDF."""
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

TIPOS_REPORTE = [
    "predictivo_general",
    "estudiantes_riesgo",
    "por_paralelo",
    "asistencia",
    "individual",
]


class ReporteGenerarRequest(BaseModel):
    """Request para generar un reporte PDF."""

    tipo: str = Field(description="Tipo de reporte a generar")
    paralelo_id: int | None = Field(default=None, description="Filtrar por paralelo (requerido para 'por_paralelo')")
    nivel_riesgo: str | None = Field(default=None, description="Filtrar por nivel de riesgo")
    estudiante_id: int | None = Field(default=None, description="ID del estudiante (requerido para 'individual')")
    fecha_desde: date | None = Field(default=None, description="Fecha desde")
    fecha_hasta: date | None = Field(default=None, description="Fecha hasta")

    @field_validator("tipo")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if v not in TIPOS_REPORTE:
            raise ValueError(f"tipo debe ser uno de: {', '.join(TIPOS_REPORTE)}")
        return v


class ReporteGeneradoItem(BaseModel):
    """Fila del historial de reportes generados."""

    id: int
    tipo: str
    nombre: str
    generado_por_nombre: str
    fecha_generacion: datetime
    parametros: dict | None = None


class ReportesListResponse(BaseModel):
    """Respuesta del historial de reportes."""

    total: int
    reportes: list[ReporteGeneradoItem]


class TipoReporteInfo(BaseModel):
    """Información de un tipo de reporte disponible."""

    tipo: str
    nombre: str
    descripcion: str
    requiere_paralelo: bool = False
    requiere_estudiante: bool = False


class TiposReporteResponse(BaseModel):
    """Lista de tipos de reporte disponibles."""

    tipos: list[TipoReporteInfo]
