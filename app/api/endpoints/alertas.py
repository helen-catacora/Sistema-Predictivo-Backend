"""Endpoints de alertas de riesgo de abandono."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import require_module
from app.core.database import get_db
from app.models import Alerta, Estudiante, Paralelo, Usuario
from app.schemas.alerta import (
    AlertaItem,
    AlertaUpdateRequest,
    AlertaUpdateResponse,
    AlertasListResponse,
)

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.get(
    "",
    response_model=AlertasListResponse,
    summary="Listar alertas",
    description="Lista alertas de riesgo con filtros opcionales.",
)
async def listar_alertas(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Visualización de Resultados")),
    estado: Annotated[str | None, Query(description="Filtrar por estado")] = None,
    tipo: Annotated[str | None, Query(description="temprana, critica o abandono")] = None,
    nivel: Annotated[str | None, Query(description="Bajo, Medio, Alto o Critico")] = None,
    paralelo_id: Annotated[int | None, Query(description="Filtrar por paralelo")] = None,
):
    q = (
        select(Alerta)
        .options(
            selectinload(Alerta.estudiante)
            .selectinload(Estudiante.paralelo),
        )
        .order_by(Alerta.fecha_creacion.desc())
    )

    if estado:
        q = q.where(Alerta.estado == estado)
    if tipo:
        q = q.where(Alerta.tipo == tipo)
    if nivel:
        q = q.where(Alerta.nivel == nivel)
    if paralelo_id:
        q = q.where(Alerta.estudiante.has(Estudiante.paralelo_id == paralelo_id))

    result = await db.execute(q)
    alertas = result.scalars().unique().all()

    items = []
    for a in alertas:
        e = a.estudiante
        items.append(AlertaItem(
            id=a.id,
            tipo=a.tipo,
            nivel=a.nivel,
            estudiante_id=e.id,
            nombre_estudiante=f"{e.nombre} {e.apellido}".strip(),
            codigo_estudiante=e.codigo_estudiante,
            paralelo=e.paralelo.nombre if e.paralelo else "",
            titulo=a.titulo,
            descripcion=a.descripcion,
            fecha_creacion=a.fecha_creacion,
            estado=a.estado,
            faltas_consecutivas=a.faltas_consecutivas,
        ))

    total_activas = sum(1 for a in alertas if a.estado == "activa")
    total_criticas = sum(1 for a in alertas if a.tipo == "critica" and a.estado == "activa")

    return AlertasListResponse(
        total=len(items),
        total_activas=total_activas,
        total_criticas=total_criticas,
        alertas=items,
    )


@router.patch(
    "/{alerta_id}",
    response_model=AlertaUpdateResponse,
    summary="Actualizar estado de alerta",
    description="Cambia el estado de una alerta (en_seguimiento, resuelta, descartada).",
)
async def actualizar_alerta(
    alerta_id: int,
    body: AlertaUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_module("Visualización de Resultados")),
):
    q = select(Alerta).where(Alerta.id == alerta_id)
    result = await db.execute(q)
    alerta = result.scalar_one_or_none()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    alerta.estado = body.estado
    alerta.observacion_resolucion = body.observacion_resolucion

    if body.estado in ("resuelta", "descartada"):
        alerta.fecha_resolucion = datetime.now(timezone.utc)
        alerta.resuelta_por_id = current_user.id

    return AlertaUpdateResponse(
        id=alerta.id,
        estado=alerta.estado,
        resuelta_por=current_user.nombre if alerta.resuelta_por_id else None,
        fecha_resolucion=alerta.fecha_resolucion,
        observacion_resolucion=alerta.observacion_resolucion,
    )
