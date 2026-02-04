"""Endpoints de asistencias (listado y actualización del día por materia y paralelo)."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user, require_module
from app.core.database import get_db
from app.models import Asistencia, Estudiante, Materia, Paralelo
from app.models import Usuario
from app.models.asistencia import EstadoAsistencia
from app.schemas.asistencia import (
    AsistenciaDiaItem,
    AsistenciaDiaResponse,
    AsistenciaDiaUpdateRequest,
)

router = APIRouter(prefix="/asistencias", tags=["asistencias"])


@router.get(
    "/dia",
    response_model=AsistenciaDiaResponse,
    summary="Asistencia del día",
    description="Lista la asistencia del día por materia y paralelo. Incluye todos los estudiantes del paralelo; si no tienen registro ese día, estado y observación van vacíos.",
)
async def listar_asistencia_dia(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("asistencias")),
    materia_id: Annotated[int, Query(description="ID de la materia")] = ...,
    paralelo_id: Annotated[int, Query(description="ID del paralelo")] = ...,
    fecha: Annotated[date | None, Query(description="Fecha del día (por defecto hoy)")] = None,
):
    """
    Devuelve todos los estudiantes del paralelo con su asistencia del día para la materia indicada.
    Si el estudiante no tiene registro de asistencia ese día, se retorna estado y observación como string vacío.
    """
    if fecha is None:
        fecha = date.today()

    # Nombre de la materia (tabla materias: id, nombre)
    r_mat = await db.execute(select(Materia).where(Materia.id == materia_id))
    materia_obj = r_mat.scalar_one_or_none()
    materia_nombre = materia_obj.nombre if materia_obj else ""

    # Nombre del paralelo (para la columna paralelo)
    r_par = await db.execute(select(Paralelo).where(Paralelo.id == paralelo_id))
    paralelo_obj = r_par.scalar_one_or_none()
    nombre_paralelo = paralelo_obj.nombre if paralelo_obj else ""

    # Todos los estudiantes del paralelo, ordenados por apellido y nombre
    q_est = (
        select(Estudiante)
        .where(Estudiante.paralelo_id == paralelo_id)
        .order_by(Estudiante.apellido, Estudiante.nombre)
    )
    result_est = await db.execute(q_est)
    estudiantes = result_est.scalars().all()
    if not estudiantes:
        return AsistenciaDiaResponse(
            materia_id=materia_id,
            materia_nombre=materia_nombre,
            total_estudiantes=0,
            total_presentes=0,
            total_ausentes=0,
            porcentaje_asistencia_dia=0.0,
            asistencias=[],
        )

    ids_estudiantes = [e.id for e in estudiantes]

    # Registros de asistencia del día para esta materia y estos estudiantes
    q_asis = select(Asistencia).where(
        Asistencia.materia_id == materia_id,
        Asistencia.fecha == fecha,
        Asistencia.estudiante_id.in_(ids_estudiantes),
    )
    result_asis = await db.execute(q_asis)
    registros = result_asis.scalars().all()
    # Un estudiante puede tener a lo sumo un registro por (fecha, materia)
    mapa = {a.estudiante_id: (a.estado, a.observacion or "") for a in registros}

    items = []
    for e in estudiantes:
        estado, observacion = mapa.get(e.id, ("", ""))
        nombre_completo = f"{e.nombre} {e.apellido}".strip()
        items.append(
            AsistenciaDiaItem(
                materia_id=materia_id,
                paralelo_id=paralelo_id,
                paralelo=nombre_paralelo,
                nombre_estudiante=nombre_completo,
                codigo_estudiante=e.codigo_estudiante,
                estado=estado,
                observacion=observacion,
            )
        )

    total_estudiantes = len(items)
    total_presentes = sum(1 for i in items if i.estado == "Presente")
    total_ausentes = total_estudiantes - total_presentes  # no presentes (sin registro, Ausente, Justificado, No Cursa)
    porcentaje_asistencia_dia = (total_presentes / total_estudiantes * 100.0) if total_estudiantes else 0.0

    return AsistenciaDiaResponse(
        materia_id=materia_id,
        materia_nombre=materia_nombre,
        total_estudiantes=total_estudiantes,
        total_presentes=total_presentes,
        total_ausentes=total_ausentes,
        porcentaje_asistencia_dia=round(porcentaje_asistencia_dia, 2),
        asistencias=items,
    )


@router.post(
    "/dia",
    status_code=status.HTTP_201_CREATED,
    summary="Crear asistencia del día",
    description="Crea los registros de asistencia del día. Body: listado de estudiantes (id, estado, observación opcional). Query: materia_id, paralelo_id. Requiere JWT.",
)
async def crear_asistencia_dia(
    body: AsistenciaDiaUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_module("asistencias")),
    materia_id: Annotated[int, Query(description="ID de la materia")] = ...,
    paralelo_id: Annotated[int, Query(description="ID del paralelo")] = ...,
    fecha: Annotated[date | None, Query(description="Fecha del día (por defecto hoy)")] = None,
):
    """
    Crea la asistencia del día para la materia y paralelo indicados.
    Cada item del body debe tener estudiante_id y estado (Presente, Ausente, Justificado, No Cursa).
    Solo se aceptan estudiantes que pertenezcan al paralelo. El usuario autenticado queda como encargado del registro.
    Si ya existe registro para ese estudiante/materia/fecha, se actualiza.
    """
    if fecha is None:
        fecha = date.today()

    # Estudiantes que pertenecen al paralelo (para validar)
    r = await db.execute(
        select(Estudiante.id).where(Estudiante.paralelo_id == paralelo_id)
    )
    ids_paralelo = {row[0] for row in r.all()}
    if not ids_paralelo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay estudiantes en el paralelo indicado",
        )

    # Registros existentes del día (materia + fecha) para estos estudiantes
    r = await db.execute(
        select(Asistencia).where(
            Asistencia.materia_id == materia_id,
            Asistencia.fecha == fecha,
            Asistencia.estudiante_id.in_(ids_paralelo),
        )
    )
    existentes = {a.estudiante_id: a for a in r.scalars().all()}

    for item in body.asistencias:
        if item.estudiante_id not in ids_paralelo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El estudiante {item.estudiante_id} no pertenece al paralelo {paralelo_id}",
            )
        if item.estudiante_id in existentes:
            reg = existentes[item.estudiante_id]
            reg.estado = item.estado
            reg.observacion = item.observacion
            reg.encargado_id = current_user.id
        else:
            nuevo = Asistencia(
                fecha=fecha,
                estado=item.estado,
                observacion=item.observacion,
                estudiante_id=item.estudiante_id,
                materia_id=materia_id,
                encargado_id=current_user.id,
            )
            db.add(nuevo)
            existentes[item.estudiante_id] = nuevo

    return {"message": "Asistencia del día creada", "registros": len(body.asistencias)}
