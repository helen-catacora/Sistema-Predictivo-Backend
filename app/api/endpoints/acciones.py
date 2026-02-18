"""Endpoints para acciones de seguimiento de predicciones."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models import Accion, Estudiante, Prediccion, Usuario
from app.schemas.accion import (
    AccionCreateRequest,
    AccionCreateResponse,
    AccionListItem,
    AccionListResponse,
)

router = APIRouter(prefix="/acciones", tags=["acciones"])


@router.post(
    "",
    response_model=AccionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear acción de seguimiento",
    description=(
        "Registra una acción de seguimiento para un estudiante. "
        "La acción se asocia automáticamente a la predicción más reciente del estudiante. "
        "(ej. entrevista con psicopedagogía, tutoría académica, derivación a bienestar estudiantil)."
    ),
    responses={
        201: {"description": "Acción creada exitosamente"},
        400: {"description": "El estudiante no tiene predicciones asociadas"},
        404: {"description": "Estudiante no encontrado"},
        401: {"description": "No autenticado"},
    },
)
async def crear_accion(
    data: AccionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Crea una acción de seguimiento para un estudiante.

    **Flujo**:
    1. Verifica que el estudiante existe
    2. Busca la predicción más reciente del estudiante
    3. Crea la acción asociada a esa predicción

    **Validaciones**:
    - El estudiante debe existir en la base de datos
    - El estudiante debe tener al menos una predicción
    - La descripción no puede estar vacía (1-2000 caracteres)

    **Permisos**: Requiere autenticación (cualquier usuario autenticado puede crear acciones)
    """
    # ── 1. Verificar que el estudiante existe ──────────────────────
    query_est = select(Estudiante).where(Estudiante.id == data.estudiante_id)
    result_est = await db.execute(query_est)
    estudiante = result_est.scalar_one_or_none()

    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró el estudiante con ID {data.estudiante_id}",
        )

    # ── 2. Buscar la predicción más reciente del estudiante ────────
    query_pred = (
        select(Prediccion)
        .where(Prediccion.estudiante_id == data.estudiante_id)
        .order_by(Prediccion.fecha_prediccion.desc(), Prediccion.id.desc())
        .limit(1)
    )
    result_pred = await db.execute(query_pred)
    prediccion = result_pred.scalar_one_or_none()

    if not prediccion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El estudiante '{estudiante.nombre} {estudiante.apellido}' no tiene predicciones asociadas. "
                   "Debe realizar una predicción antes de registrar acciones.",
        )

    # ── 3. Crear la acción ─────────────────────────────────────────
    nueva_accion = Accion(
        descripcion=data.descripcion,
        fecha=data.fecha,
        prediccion_id=prediccion.id,
    )

    db.add(nueva_accion)
    await db.flush()  # Obtener el ID antes del commit
    await db.commit()
    await db.refresh(nueva_accion)

    # ── 4. Preparar respuesta con datos del estudiante ────────────
    nombre_estudiante = f"{estudiante.nombre} {estudiante.apellido}".strip()

    return AccionCreateResponse(
        id=nueva_accion.id,
        descripcion=nueva_accion.descripcion,
        fecha=nueva_accion.fecha,
        prediccion_id=prediccion.id,
        estudiante_id=estudiante.id,
        estudiante_nombre=nombre_estudiante,
    )


@router.get(
    "",
    response_model=AccionListResponse,
    summary="Listar acciones de seguimiento",
    description="Devuelve el listado de acciones registradas con información del estudiante y predicción asociados.",
    responses={
        200: {"description": "Lista de acciones"},
        401: {"description": "No autenticado"},
    },
)
async def listar_acciones(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    estudiante_id: Annotated[
        int | None,
        Query(description="Filtrar por ID de estudiante"),
    ] = None,
    prediccion_id: Annotated[
        int | None,
        Query(description="Filtrar por ID de predicción"),
    ] = None,
    limite: Annotated[
        int,
        Query(description="Número máximo de resultados", ge=1, le=100),
    ] = 50,
):
    """
    Lista todas las acciones registradas con opciones de filtrado.

    **Filtros disponibles**:
    - `estudiante_id`: Filtra acciones del estudiante específico
    - `prediccion_id`: Filtra acciones de una predicción específica
    - `limite`: Limita el número de resultados (máx. 100)

    **Permisos**: Requiere autenticación
    """
    # ── 1. Query base con joins ────────────────────────────────────
    query = (
        select(Accion)
        .join(Prediccion, Prediccion.id == Accion.prediccion_id)
        .join(Estudiante, Estudiante.id == Prediccion.estudiante_id)
        .options(
            selectinload(Accion.prediccion).selectinload(Prediccion.estudiante)
        )
        .order_by(Accion.fecha.desc(), Accion.id.desc())
    )

    # ── 2. Aplicar filtros opcionales ──────────────────────────────
    if estudiante_id is not None:
        query = query.where(Estudiante.id == estudiante_id)

    if prediccion_id is not None:
        query = query.where(Accion.prediccion_id == prediccion_id)

    query = query.limit(limite)

    # ── 3. Ejecutar query ──────────────────────────────────────────
    result = await db.execute(query)
    acciones = result.scalars().unique().all()

    # ── 4. Construir respuesta ─────────────────────────────────────
    items = []
    for accion in acciones:
        estudiante = accion.prediccion.estudiante
        nombre_estudiante = f"{estudiante.nombre} {estudiante.apellido}".strip()

        items.append(
            AccionListItem(
                id=accion.id,
                descripcion=accion.descripcion,
                fecha=accion.fecha,
                prediccion_id=accion.prediccion_id,
                estudiante_id=estudiante.id,
                estudiante_nombre=nombre_estudiante,
                fecha_prediccion=accion.prediccion.fecha_prediccion,
                nivel_riesgo=accion.prediccion.nivel_riesgo,
            )
        )

    return AccionListResponse(total=len(items), acciones=items)
