"""Endpoints de gestiones académicas."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user, require_module
from app.core.database import get_db
from app.models import GestionAcademica, Usuario
from app.schemas.gestion_academica import (
    GestionAcademicaCreate,
    GestionAcademicaItem,
    GestionAcademicaListResponse,
)

router = APIRouter(prefix="/gestiones", tags=["gestiones"])


@router.get(
    "",
    response_model=GestionAcademicaListResponse,
    summary="Listar gestiones académicas",
)
async def listar_gestiones(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = select(GestionAcademica).order_by(GestionAcademica.id.desc())
    result = await db.execute(q)
    gestiones = result.scalars().all()

    items = [
        GestionAcademicaItem(
            id=g.id,
            nombre=g.nombre,
            fecha_inicio=g.fecha_inicio,
            fecha_fin=g.fecha_fin,
            activa=g.activa,
        )
        for g in gestiones
    ]
    return GestionAcademicaListResponse(gestiones=items)


@router.post(
    "",
    response_model=GestionAcademicaItem,
    status_code=status.HTTP_201_CREATED,
    summary="Crear gestión académica",
)
async def crear_gestion(
    body: GestionAcademicaCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Gestión de Usuarios")),
):
    # Verificar nombre único
    existing = await db.execute(
        select(GestionAcademica).where(GestionAcademica.nombre == body.nombre)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Ya existe una gestión con nombre '{body.nombre}'")

    gestion = GestionAcademica(
        nombre=body.nombre,
        fecha_inicio=body.fecha_inicio,
        fecha_fin=body.fecha_fin,
        activa=False,
    )
    db.add(gestion)
    await db.flush()

    return GestionAcademicaItem(
        id=gestion.id,
        nombre=gestion.nombre,
        fecha_inicio=gestion.fecha_inicio,
        fecha_fin=gestion.fecha_fin,
        activa=gestion.activa,
    )


@router.patch(
    "/{gestion_id}/activar",
    response_model=GestionAcademicaItem,
    summary="Activar gestión académica",
    description="Activa una gestión y desactiva la anterior automáticamente.",
)
async def activar_gestion(
    gestion_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Gestión de Usuarios")),
):
    q = select(GestionAcademica).where(GestionAcademica.id == gestion_id)
    result = await db.execute(q)
    gestion = result.scalar_one_or_none()
    if not gestion:
        raise HTTPException(status_code=404, detail="Gestión no encontrada")

    # Desactivar todas las gestiones activas
    await db.execute(
        update(GestionAcademica)
        .where(GestionAcademica.activa == True)
        .values(activa=False)
    )

    # Activar la seleccionada
    gestion.activa = True

    return GestionAcademicaItem(
        id=gestion.id,
        nombre=gestion.nombre,
        fecha_inicio=gestion.fecha_inicio,
        fecha_fin=gestion.fecha_fin,
        activa=gestion.activa,
    )
