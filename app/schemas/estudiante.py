"""Esquemas para estudiantes (tabla de sección, importación masiva, perfil)."""
from datetime import date, datetime

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


# ── Perfil individual del estudiante ──────────────────────────────


class PerfilEncargado(BaseModel):
    id: int
    nombre: str


class PerfilParalelo(BaseModel):
    id: int
    nombre: str
    semestre: str | None = None
    encargado: PerfilEncargado | None = None


class PerfilDatosBasicos(BaseModel):
    id: int
    codigo_estudiante: str
    nombre_completo: str
    edad: int | None = None
    genero: str | None = None
    carrera: str | None = None
    paralelo: PerfilParalelo | None = None


class PerfilSociodemografico(BaseModel):
    fecha_nacimiento: date | None = None
    grado: str | None = None
    estrato_socioeconomico: str | None = None
    ocupacion_laboral: str | None = None
    con_quien_vive: str | None = None
    apoyo_economico: str | None = None
    modalidad_ingreso: str | None = None
    tipo_colegio: str | None = None


class PerfilAsistenciaConteo(BaseModel):
    presentes: int = 0
    ausentes: int = 0
    justificados: int = 0


class PerfilMateriaAsistencia(BaseModel):
    materia_id: int
    nombre: str
    gestion_academica: str | None = None
    porcentaje_asistencia: float = 0.0
    asistencias: PerfilAsistenciaConteo = Field(default_factory=PerfilAsistenciaConteo)


class PerfilDesempenioAcademico(BaseModel):
    porcentaje_asistencia_general: float = 0.0
    faltas_consecutivas: int = 0
    materias: list[PerfilMateriaAsistencia] = Field(default_factory=list)


class PerfilPrediccionActual(BaseModel):
    id: int
    probabilidad_abandono: float
    nivel_riesgo: str
    clasificacion: str = Field(description="Abandona o No Abandona")
    fecha_prediccion: date
    tipo: str
    version_modelo: str | None = None
    features_utilizadas: dict | None = None


class PerfilPrediccionHistorial(BaseModel):
    id: int
    fecha_prediccion: date
    probabilidad_abandono: float
    nivel_riesgo: str


class PerfilRiesgoPrediccion(BaseModel):
    prediccion_actual: PerfilPrediccionActual | None = None
    historial: list[PerfilPrediccionHistorial] = Field(default_factory=list)


class PerfilAlerta(BaseModel):
    id: int
    tipo: str
    nivel: str
    titulo: str
    descripcion: str
    fecha_creacion: datetime
    estado: str
    faltas_consecutivas: int = 0
    fecha_resolucion: datetime | None = None
    observacion_resolucion: str | None = None


class PerfilAlertas(BaseModel):
    activas: list[PerfilAlerta] = Field(default_factory=list)
    historial: list[PerfilAlerta] = Field(default_factory=list)


class PerfilAccion(BaseModel):
    id: int
    descripcion: str
    fecha: date
    prediccion_id: int


class EstudiantePerfilResponse(BaseModel):
    """Respuesta completa del perfil de un estudiante."""

    datos_basicos: PerfilDatosBasicos
    datos_sociodemograficos: PerfilSociodemografico
    desempenio_academico: PerfilDesempenioAcademico
    riesgo_y_prediccion: PerfilRiesgoPrediccion
    alertas: PerfilAlertas
    acciones: list[PerfilAccion] = Field(default_factory=list)
