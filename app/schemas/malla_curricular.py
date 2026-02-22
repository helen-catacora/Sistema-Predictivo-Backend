"""Esquemas para importación de malla curricular."""
from pydantic import BaseModel


class ImportacionMallaErrorItem(BaseModel):
    """Error individual durante la importación de malla curricular."""

    fila: int
    detalle: str


class ImportacionMallaResponse(BaseModel):
    """Respuesta de la importación de malla curricular desde Excel."""

    nombre_archivo: str
    filas_procesadas: int
    registros_creados: int
    materias_creadas: int
    ya_existentes: int
    errores: list[ImportacionMallaErrorItem]
