"""Modelos SQLAlchemy (tablas de la base de datos)."""
from app.models.role import Rol
from app.models.user import Usuario
from app.models.semester import Semestre
from app.models.area import Area
from app.models.paralelo import Paralelo
from app.models.student import Estudiante
from app.models.subject import Materia
from app.models.malla_curricular import MallaCurricular
from app.models.inscripcion import Inscripcion
from app.models.asistencia import Asistencia, EstadoAsistencia
from app.models.prediccion import Prediccion, NivelRiesgo
from app.models.accion import Accion
from app.models.modulo import Modulo, UsuarioModulo
from app.models.gestion_academica import GestionAcademica
from app.models.lote_prediccion import LotePrediccion, EstadoLote
from app.models.alerta import Alerta, TipoAlerta, EstadoAlerta
from app.models.reporte_generado import ReporteGenerado
from app.models.lote_importacion_estudiante import LoteImportacionEstudiante

__all__ = [
    "Rol",
    "Usuario",
    "Semestre",
    "Area",
    "Paralelo",
    "Estudiante",
    "Materia",
    "MallaCurricular",
    "Inscripcion",
    "Asistencia",
    "EstadoAsistencia",
    "Prediccion",
    "NivelRiesgo",
    "Accion",
    "Modulo",
    "UsuarioModulo",
    "GestionAcademica",
    "LotePrediccion",
    "EstadoLote",
    "Alerta",
    "TipoAlerta",
    "EstadoAlerta",
    "ReporteGenerado",
    "LoteImportacionEstudiante",
]
