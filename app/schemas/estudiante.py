"""Esquemas para estudiantes (tabla de sección)."""
from pydantic import BaseModel, Field


class EstudianteTablaItem(BaseModel):
    """Fila para la tabla de estudiantes (nombre, matrícula, % asistencia, riesgo)."""

    id: int = Field(description="ID del estudiante (para Ver perfil)")
    nombre_completo: str = Field(description="Nombre y apellido del estudiante")
    carrera: str | None = Field(default=None, description="Carrera/área (ej. Ing. de Sistemas). Opcional.")
    codigo_estudiante: str = Field(description="ID / Matrícula (ej. EMI-2024-0012)")
    porcentaje_asistencia: float = Field(description="Porcentaje de asistencia (0-100), calculado desde asistencias")
    nivel_riesgo: str = Field(description="Nivel de riesgo: ALTO, MEDIO, BAJO. Por ahora siempre ALTO (ML posterior).")


class EstudianteTablaResponse(BaseModel):
    """Respuesta del endpoint de tabla de estudiantes."""

    estudiantes: list[EstudianteTablaItem] = Field(description="Lista de estudiantes para renderizar la tabla")
