"""Esquemas para predicciones de abandono."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class DatosAcademicos(BaseModel):
    """Datos académicos para la predicción."""
    materias_inscritas: int = Field(description="Número de materias inscritas (Mat)")
    materias_reprobadas: int = Field(default=0, description="Materias reprobadas (Rep)")
    materias_segunda_oportunidad: int = Field(default=0, description="Materias en 2da oportunidad (2T)")
    promedio_general: float = Field(description="Promedio general (Prom)")


class DatosSociodemograficos(BaseModel):
    """Datos sociodemográficos para la predicción (todos opcionales)."""
    edad: int | None = Field(default=None, description="Edad del estudiante")
    grado: str | None = Field(default=None, description="Civil o Militar")
    genero: str | None = Field(default=None, description="Masculino o Femenino")
    estrato_socioeconomico: str | None = Field(default=None, description="Alto, Bajo o Medio")
    ocupacion_laboral: str | None = Field(default=None, description="Si o No")
    con_quien_vive: str | None = Field(default=None, description="Con Familiares, Con mis padres, Solo/a, etc.")
    apoyo_economico: str | None = Field(default=None, description="Ninguno, Parcial o Total")
    modalidad_ingreso: str | None = Field(default=None, description="Admision Especial, Curso Preuniversitario/Intensivo, etc.")
    tipo_colegio: str | None = Field(default=None, description="Convenio, Privado o Publico")


# --- Predicción individual ---

class PrediccionIndividualRequest(BaseModel):
    """Request para predicción individual."""
    estudiante_id: int = Field(description="ID del estudiante en la BD")
    datos_academicos: DatosAcademicos
    datos_sociodemograficos: DatosSociodemograficos | None = Field(
        default=None,
        description="Si no se envía, se toman de la BD del estudiante",
    )


class PrediccionIndividualResponse(BaseModel):
    """Resultado de una predicción individual."""
    prediccion_id: int
    estudiante_id: int
    nombre_estudiante: str
    probabilidad_abandono: float
    nivel_riesgo: str
    fecha_prediccion: date
    features_utilizadas: dict | None = None
    alerta_generada: bool = False


# --- Historial ---

class PrediccionHistorialItem(BaseModel):
    """Fila del historial de predicciones."""
    id: int
    estudiante_id: int
    nombre_estudiante: str
    codigo_estudiante: str
    probabilidad_abandono: float
    nivel_riesgo: str
    fecha_prediccion: date
    tipo: str
    lote_id: int | None = None
    version_modelo: str | None = None


class PrediccionHistorialResponse(BaseModel):
    """Respuesta paginada del historial de predicciones."""
    total: int
    pagina: int
    total_paginas: int
    predicciones: list[PrediccionHistorialItem]


# --- Evolución de un estudiante ---

class EvolucionItem(BaseModel):
    """Punto de evolución temporal."""
    fecha: date
    probabilidad: float
    nivel: str


class AccionItem(BaseModel):
    """Acción tomada sobre una predicción."""
    id: int
    descripcion: str
    fecha: date


class EstudianteEvolucionResponse(BaseModel):
    """Historial de predicciones y evolución de un estudiante."""
    estudiante_id: int
    nombre_estudiante: str
    codigo_estudiante: str
    prediccion_actual: EvolucionItem | None = None
    evolucion: list[EvolucionItem]
    datos_sociodemograficos: dict | None = None
    acciones_tomadas: list[AccionItem]


# --- Lotes ---

class LotePrediccionItem(BaseModel):
    """Fila de la lista de lotes."""
    id: int
    nombre_archivo: str
    fecha_carga: datetime
    usuario_nombre: str
    estado: str
    total_estudiantes: int
    total_procesados: int
    total_alto_riesgo: int
    total_critico: int
    version_modelo: str


class LotePrediccionListResponse(BaseModel):
    """Lista de lotes de predicción."""
    lotes: list[LotePrediccionItem]


class LoteDetalleResponse(BaseModel):
    """Detalle de un lote con sus predicciones."""
    id: int
    nombre_archivo: str
    fecha_carga: datetime
    usuario_nombre: str
    estado: str
    total_estudiantes: int
    total_procesados: int
    total_alto_riesgo: int
    total_medio_riesgo: int
    total_bajo_riesgo: int
    total_critico: int
    version_modelo: str
    predicciones: list[PrediccionHistorialItem]


# --- Dashboard ---

class ResumenGeneral(BaseModel):
    """Resumen general del dashboard."""
    total_estudiantes: int
    total_predicciones_activas: int
    total_alto_riesgo: int
    total_critico: int
    total_medio_riesgo: int
    total_bajo_riesgo: int
    porcentaje_alto_riesgo: float
    total_alertas_activas: int
    total_alertas_criticas: int


class DistribucionRiesgoItem(BaseModel):
    """Distribución por nivel de riesgo."""
    nivel: str
    cantidad: int
    porcentaje: float


class DistribucionParaleloItem(BaseModel):
    """Distribución por paralelo."""
    paralelo: str
    area: str
    total: int
    alto_riesgo: int
    critico: int


class DashboardResponse(BaseModel):
    """Respuesta del dashboard de predicciones."""
    resumen_general: ResumenGeneral
    distribucion_riesgo: list[DistribucionRiesgoItem]
    distribucion_por_paralelo: list[DistribucionParaleloItem]


class UltimaImportacionMasiva(BaseModel):
    """Detalle del último archivo subido para predicción masiva."""
    nombre_archivo: str
    fecha_carga: datetime
    cantidad_registros: int


class ResumenImportacionMasivaResponse(BaseModel):
    """Resumen de importaciones masivas: total de cargas y detalle de la última."""
    total_importaciones: int
    ultima_importacion: UltimaImportacionMasiva | None
