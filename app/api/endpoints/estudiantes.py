"""Endpoints de estudiantes (tabla de sección con asistencia y riesgo)."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Asistencia, Estudiante
from app.models.paralelo import Paralelo
from app.models.asistencia import EstadoAsistencia
from app.schemas.estudiante import EstudianteTablaItem, EstudianteTablaResponse

router = APIRouter(prefix="/estudiantes", tags=["estudiantes"])


@router.get(
    "/tabla",
    response_model=EstudianteTablaResponse,
    summary="Tabla de estudiantes para sección",
    description="Lista estudiantes con nombre, matrícula, % asistencia (desde tabla asistencias) y nivel_riesgo (siempre ALTO; luego vendrá de ML).",
    responses={
        200: {"description": "Lista de estudiantes para renderizar la tabla"},
    },
)
async def get_estudiantes_tabla(
    db: AsyncSession = Depends(get_db),
    paralelo_id: Annotated[int | None, Query(description="Filtrar por paralelo")] = None,
    fecha_desde: Annotated[date | None, Query(description="Inicio del periodo para % asistencia")] = None,
    fecha_hasta: Annotated[date | None, Query(description="Fin del periodo para % asistencia")] = None,
):
    """
    Devuelve los datos para renderizar la tabla de estudiantes (nombre, matrícula, % asistencia, promedio, riesgo).
    - **% asistencia:** calculado desde `asistencias` (Presente + Justificado sobre total Presente+Ausente+Justificado; No Cursa no cuenta).
    - **Promedio:** no existe en BD aún; se devuelve `null`.
    - **Nivel de riesgo:** siempre `"ALTO"`; en el futuro vendrá del modelo de ML.
    """
    # Estudiantes (opcionalmente por paralelo), con paralelo y área para carrera
    q = (
        select(Estudiante)
        .options(selectinload(Estudiante.paralelo).selectinload(Paralelo.area))
        .order_by(Estudiante.apellido, Estudiante.nombre)
    )
    if paralelo_id is not None:
        q = q.where(Estudiante.paralelo_id == paralelo_id)
    result = await db.execute(q)
    estudiantes = result.scalars().unique().all()

    # Subconsulta: por cada estudiante, contar presentes y total (excl. No Cursa)
    condicion_presente = Asistencia.estado.in_([EstadoAsistencia.PRESENTE, EstadoAsistencia.JUSTIFICADO])
    condicion_total = Asistencia.estado.in_(
        [EstadoAsistencia.PRESENTE, EstadoAsistencia.AUSENTE, EstadoAsistencia.JUSTIFICADO]
    )
    presentes_expr = func.sum(case((condicion_presente, 1), else_=0))
    total_expr = func.sum(case((condicion_total, 1), else_=0))

    subq = (
        select(
            Asistencia.estudiante_id,
            presentes_expr.label("presentes"),
            total_expr.label("total"),
        )
        .group_by(Asistencia.estudiante_id)
    )
    if fecha_desde is not None:
        subq = subq.where(Asistencia.fecha >= fecha_desde)
    if fecha_hasta is not None:
        subq = subq.where(Asistencia.fecha <= fecha_hasta)

    res_asis = await db.execute(subq)
    filas_asis = {r.estudiante_id: (r.presentes or 0, r.total or 0) for r in res_asis}

    items = []
    for e in estudiantes:
        presentes, total = filas_asis.get(e.id, (0, 0))
        porcentaje = round(100.0 * presentes / total, 1) if total else 0.0
        nombre_completo = f"{e.nombre} {e.apellido}".strip()
        # Carrera: usar nombre del área si está cargado (paralelo -> area)
        carrera = None
        if e.paralelo and e.paralelo.area:
            carrera = e.paralelo.area.nombre

        items.append(
            EstudianteTablaItem(
                id=e.id,
                nombre_completo=nombre_completo,
                carrera=carrera,
                codigo_estudiante=e.codigo_estudiante,
                porcentaje_asistencia=porcentaje,
                nivel_riesgo="ALTO",
            )
        )

    return EstudianteTablaResponse(estudiantes=items)
