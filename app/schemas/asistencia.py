"""Esquemas para asistencias (listado y actualización del día)."""
from pydantic import BaseModel, Field, field_validator

ESTADOS_ASISTENCIA = ("Presente", "Ausente", "Justificado", "No Cursa")


class AsistenciaDiaUpdateItem(BaseModel):
    """Item para actualizar asistencia del día: id del estudiante y estado (y opcional observación)."""

    estudiante_id: int = Field(description="ID del estudiante")
    estado: str = Field(description="Estado: Presente, Ausente, Justificado, No Cursa")
    observacion: str | None = Field(default=None, description="Observación opcional")

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: str) -> str:
        if v not in ESTADOS_ASISTENCIA:
            raise ValueError(f"estado debe ser uno de: {', '.join(ESTADOS_ASISTENCIA)}")
        return v


class AsistenciaDiaUpdateRequest(BaseModel):
    """Body para actualizar la asistencia del día: listado de estudiantes con estado."""

    asistencias: list[AsistenciaDiaUpdateItem] = Field(description="Listado de asistencias (estudiante_id, estado, observación opcional)")


class AsistenciaDiaItem(BaseModel):
    """Fila de asistencia del día por estudiante (materia + paralelo)."""

    estudiante_id: int = Field(description="ID del estudiante")
    materia_id: int = Field(description="ID de la materia consultada (siempre el del request)")
    paralelo_id: int = Field(description="ID del paralelo")
    paralelo: str = Field(description="Nombre del paralelo")
    nombre_estudiante: str = Field(description="Nombre completo del estudiante")
    codigo_estudiante: str = Field(description="Código / matrícula del estudiante")
    estado: str = Field(description="Estado de la asistencia (Presente, Ausente, Justificado, No Cursa). Vacío si no hay registro del día.")
    observacion: str = Field(description="Observación del registro de asistencia. Vacío si no hay registro del día.")


class AsistenciaDiaResponse(BaseModel):
    """Respuesta del listado de asistencia del día."""

    materia_id: int = Field(description="ID de la materia consultada (para verificar que coincide con el request)")
    materia_nombre: str = Field(description="Nombre de la materia consultada")
    total_estudiantes: int = Field(description="Total de estudiantes del paralelo para esta materia")
    total_presentes: int = Field(description="Total de estudiantes presentes en el día")
    total_ausentes: int = Field(description="Total de estudiantes no presentes (ausentes, justificados, no cursa o sin registro)")
    porcentaje_asistencia_dia: float = Field(description="Porcentaje de asistencia del día (presentes / total * 100)")
    asistencias: list[AsistenciaDiaItem] = Field(description="Lista de estudiantes con su asistencia del día (estado/observación vacíos si no hay registro)")
