"""Esquemas para estudiantes (tabla de sección e importación masiva)."""
from datetime import date

from pydantic import BaseModel, Field


class EstudianteTablaItem(BaseModel):
    """Fila para la tabla de estudiantes (nombre, matrícula, % asistencia, riesgo)."""

    id: int = Field(description="ID del estudiante (para Ver perfil)")
    nombre_completo: str = Field(description="Nombre y apellido del estudiante")
    carrera: str | None = Field(default=None, description="Carrera/área (ej. Ing. de Sistemas). Opcional.")
    codigo_estudiante: str = Field(description="ID / Matrícula (ej. EMI-2024-0012)")
    porcentaje_asistencia: float = Field(description="Porcentaje de asistencia (0-100), calculado desde asistencias")
    nivel_riesgo: str | None = Field(default=None, description="Nivel de riesgo de la última predicción ML: Bajo, Medio, Alto, Critico. Null si no tiene predicción.")
    probabilidad_abandono: float | None = Field(default=None, description="Probabilidad de abandono (0.0-1.0) de la última predicción ML.")
    clasificacion_abandono: str | None = Field(default=None, description="Clasificación binaria: Abandona o No Abandona, derivada de la probabilidad (>=0.5).")


class EstudianteTablaResponse(BaseModel):
    """Respuesta del endpoint de tabla de estudiantes."""

    estudiantes: list[EstudianteTablaItem] = Field(description="Lista de estudiantes para renderizar la tabla")


class EstudianteSociodemograficoUpdate(BaseModel):
    """Datos sociodemográficos del estudiante (todos opcionales)."""

    fecha_nacimiento: date | None = Field(default=None, description="Fecha de nacimiento")
    genero: str | None = Field(default=None, description="Masculino o Femenino")
    grado: str | None = Field(default=None, description="Civil o Militar")
    estrato_socioeconomico: str | None = Field(default=None, description="Alto, Bajo o Medio")
    ocupacion_laboral: str | None = Field(default=None, description="Si o No")
    con_quien_vive: str | None = Field(default=None, description="Con Familiares, Con mis padres, Solo/a, etc.")
    apoyo_economico: str | None = Field(default=None, description="Ninguno, Parcial o Total")
    modalidad_ingreso: str | None = Field(default=None, description="Admision Especial, Curso Preuniversitario/Intensivo, etc.")
    tipo_colegio: str | None = Field(default=None, description="Convenio, Privado o Publico")


# ── Importación masiva ──────────────────────────────────────────────


class ImportacionErrorItem(BaseModel):
    """Error individual durante la importación de una fila."""

    fila: int = Field(description="Número de fila en el Excel (1-indexed, sin contar encabezado)")
    codigo: str | None = Field(default=None, description="Código del estudiante (si se pudo leer)")
    mensaje: str = Field(description="Descripción del error")


class ImportacionResumen(BaseModel):
    """Contadores de entidades creadas durante la importación."""

    areas_creadas: int = 0
    semestres_creados: int = 0
    paralelos_creados: int = 0
    materias_creadas: int = 0
    inscripciones_creadas: int = 0
    inscripciones_existentes: int = 0
    mallas_creadas: int = 0


class ImportacionEstudiantesResponse(BaseModel):
    """Respuesta del endpoint de importación masiva de estudiantes."""

    nombre_archivo: str = Field(description="Nombre del archivo subido")
    total_filas: int = Field(description="Total de filas procesadas")
    estudiantes_creados: int = Field(default=0)
    estudiantes_actualizados: int = Field(default=0)
    total_errores: int = Field(default=0)
    errores: list[ImportacionErrorItem] = Field(default_factory=list)
    resumen: ImportacionResumen = Field(default_factory=ImportacionResumen)
