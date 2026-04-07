"""Esquemas para entrenamiento/reentrenamiento del modelo ML."""
from datetime import datetime

from pydantic import BaseModel


class MetricasModelo(BaseModel):
    """Métricas de evaluación de un modelo ML."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    confusion_matrix: list[list[int]] | None = None


class EntrenamientoIniciarResponse(BaseModel):
    """Respuesta al iniciar un entrenamiento."""
    entrenamiento_id: int
    estado: str
    mensaje: str


class EntrenamientoEstadoResponse(BaseModel):
    """Estado actual de un entrenamiento (para polling)."""
    id: int
    estado: str
    fecha_inicio: datetime
    fecha_fin: datetime | None = None
    nombre_archivo: str
    total_registros: int
    tipo_mejor_modelo: str | None = None
    metricas_nuevo: MetricasModelo | None = None
    metricas_actual: MetricasModelo | None = None
    parametros_modelo: dict | None = None
    mensaje_error: str | None = None


class EntrenamientoDecisionResponse(BaseModel):
    """Respuesta al aceptar o rechazar un modelo candidato."""
    mensaje: str
    version_nueva: str | None = None


class EntrenamientoHistorialItem(BaseModel):
    """Fila del historial de entrenamientos."""
    id: int
    fecha_inicio: datetime
    fecha_fin: datetime | None = None
    estado: str
    nombre_archivo: str
    total_registros: int
    tipo_mejor_modelo: str | None = None
    f1_nuevo: float | None = None
    f1_actual: float | None = None
    usuario_nombre: str
    version_generada: str | None = None


class EntrenamientoHistorialResponse(BaseModel):
    """Respuesta paginada del historial de entrenamientos."""
    total: int
    entrenamientos: list[EntrenamientoHistorialItem]


class ModeloActualResponse(BaseModel):
    """Información del modelo actualmente en producción."""
    version: str
    tipo_modelo: str
    metricas: MetricasModelo
    n_features: int
    fecha_entrenamiento: str | None = None
