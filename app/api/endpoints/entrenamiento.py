"""Endpoints de entrenamiento/reentrenamiento del modelo ML."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import Usuario
from app.models.entrenamiento_modelo import EntrenamientoModelo
from app.schemas.entrenamiento import (
    EntrenamientoDecisionResponse,
    EntrenamientoEstadoResponse,
    EntrenamientoHistorialItem,
    EntrenamientoHistorialResponse,
    EntrenamientoIniciarResponse,
    MetricasModelo,
    ModeloActualResponse,
)
from app.services import entrenamiento_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/entrenamiento", tags=["entrenamiento"])

# Pool de threads para entrenamiento (máximo 1 simultáneo)
_executor = ThreadPoolExecutor(max_workers=1)

REQUIRED_COLUMNS = entrenamiento_service.REQUIRED_COLUMNS


# ------------------------------------------------------------------
# POST /entrenamiento/iniciar
# ------------------------------------------------------------------
@router.post(
    "/iniciar",
    response_model=EntrenamientoIniciarResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar entrenamiento del modelo",
    description="Sube un Excel (.xlsx) con datos de entrenamiento y lanza el proceso en background.",
)
async def iniciar_entrenamiento(
    request: Request,
    archivo: UploadFile = File(..., description="Archivo Excel (.xlsx) con datos de entrenamiento"),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Validar extensión
    if not archivo.filename or not archivo.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .xlsx")

    # Verificar que no haya otro entrenamiento en curso
    en_curso = await db.execute(
        select(func.count()).select_from(EntrenamientoModelo).where(
            EntrenamientoModelo.estado.in_(["pendiente", "entrenando"])
        )
    )
    if (en_curso.scalar() or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un entrenamiento en curso. Espere a que termine antes de iniciar otro.",
        )

    # Leer Excel
    try:
        contents = await archivo.read()
        df = pd.read_excel(BytesIO(contents), engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer el archivo: {e}")

    # Validar columnas requeridas
    columnas_faltantes = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if columnas_faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Columnas faltantes en el Excel: {', '.join(columnas_faltantes)}",
        )

    # Validar mínimo de registros
    if len(df) < 50:
        raise HTTPException(
            status_code=400,
            detail=f"Se requieren al menos 50 registros, el archivo tiene {len(df)}.",
        )

    # Crear registro de entrenamiento
    entrenamiento = EntrenamientoModelo(
        nombre_archivo=archivo.filename,
        total_registros=len(df),
        usuario_id=current_user.id,
        estado="pendiente",
    )
    db.add(entrenamiento)
    await db.flush()
    entrenamiento_id = entrenamiento.id

    # Lanzar entrenamiento en background
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        entrenamiento_service.entrenar_modelo,
        df,
        entrenamiento_id,
        settings.database_url_sync,
        settings.ml_model_dir,
    )

    return EntrenamientoIniciarResponse(
        entrenamiento_id=entrenamiento_id,
        estado="pendiente",
        mensaje="Entrenamiento iniciado. Use GET /entrenamiento/{id}/estado para consultar el progreso.",
    )


# ------------------------------------------------------------------
# GET /entrenamiento/{id}/estado
# ------------------------------------------------------------------
@router.get(
    "/{entrenamiento_id}/estado",
    response_model=EntrenamientoEstadoResponse,
    summary="Estado de un entrenamiento",
    description="Polling: retorna el estado actual y métricas si ya completó.",
)
async def estado_entrenamiento(
    entrenamiento_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(EntrenamientoModelo).where(EntrenamientoModelo.id == entrenamiento_id)
    )
    ent = result.scalar_one_or_none()
    if not ent:
        raise HTTPException(status_code=404, detail="Entrenamiento no encontrado")

    metricas_nuevo = None
    if ent.metricas_nuevo:
        metricas_nuevo = MetricasModelo(**ent.metricas_nuevo)

    metricas_actual = None
    if ent.metricas_actual:
        metricas_actual = MetricasModelo(**ent.metricas_actual)

    return EntrenamientoEstadoResponse(
        id=ent.id,
        estado=ent.estado,
        fecha_inicio=ent.fecha_inicio,
        fecha_fin=ent.fecha_fin,
        nombre_archivo=ent.nombre_archivo,
        total_registros=ent.total_registros,
        tipo_mejor_modelo=ent.tipo_mejor_modelo,
        metricas_nuevo=metricas_nuevo,
        metricas_actual=metricas_actual,
        parametros_modelo=ent.parametros_modelo,
        mensaje_error=ent.mensaje_error,
    )


# ------------------------------------------------------------------
# POST /entrenamiento/{id}/aceptar
# ------------------------------------------------------------------
@router.post(
    "/{entrenamiento_id}/aceptar",
    response_model=EntrenamientoDecisionResponse,
    summary="Aceptar modelo candidato",
    description="Reemplaza el modelo actual con el candidato entrenado.",
)
async def aceptar(
    entrenamiento_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(EntrenamientoModelo).where(EntrenamientoModelo.id == entrenamiento_id)
    )
    ent = result.scalar_one_or_none()
    if not ent:
        raise HTTPException(status_code=404, detail="Entrenamiento no encontrado")
    if ent.estado != "completado":
        raise HTTPException(status_code=400, detail=f"Solo se pueden aceptar entrenamientos completados (estado actual: {ent.estado})")

    try:
        version = entrenamiento_service.aceptar_modelo(entrenamiento_id, settings.ml_model_dir)
        entrenamiento_service.recargar_servicio(request.app.state, settings.ml_model_dir)
    except Exception as e:
        logger.exception("Error al aceptar modelo %d", entrenamiento_id)
        raise HTTPException(status_code=500, detail=f"Error al reemplazar el modelo: {e}")

    ent.estado = "aceptado"
    ent.aceptado_por_usuario_id = current_user.id
    ent.fecha_decision = datetime.now()
    await db.flush()

    return EntrenamientoDecisionResponse(
        mensaje="Modelo reemplazado exitosamente. Las predicciones futuras usarán el nuevo modelo.",
        version_nueva=version,
    )


# ------------------------------------------------------------------
# POST /entrenamiento/{id}/rechazar
# ------------------------------------------------------------------
@router.post(
    "/{entrenamiento_id}/rechazar",
    response_model=EntrenamientoDecisionResponse,
    summary="Rechazar modelo candidato",
    description="Descarta el modelo candidato sin modificar el modelo actual.",
)
async def rechazar(
    entrenamiento_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(EntrenamientoModelo).where(EntrenamientoModelo.id == entrenamiento_id)
    )
    ent = result.scalar_one_or_none()
    if not ent:
        raise HTTPException(status_code=404, detail="Entrenamiento no encontrado")
    if ent.estado != "completado":
        raise HTTPException(status_code=400, detail=f"Solo se pueden rechazar entrenamientos completados (estado actual: {ent.estado})")

    entrenamiento_service.rechazar_modelo(entrenamiento_id, settings.ml_model_dir)

    ent.estado = "rechazado"
    ent.aceptado_por_usuario_id = current_user.id
    ent.fecha_decision = datetime.now()
    await db.flush()

    return EntrenamientoDecisionResponse(
        mensaje="Modelo candidato descartado. El modelo actual no fue modificado.",
    )


# ------------------------------------------------------------------
# GET /entrenamiento/historial
# ------------------------------------------------------------------
@router.get(
    "/historial",
    response_model=EntrenamientoHistorialResponse,
    summary="Historial de entrenamientos",
)
async def historial(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
    limite: int = Query(default=20, ge=1, le=100),
):
    q = (
        select(EntrenamientoModelo)
        .options(selectinload(EntrenamientoModelo.usuario))
        .order_by(EntrenamientoModelo.fecha_inicio.desc())
        .limit(limite)
    )
    result = await db.execute(q)
    entrenamientos = result.scalars().unique().all()

    total_q = select(func.count()).select_from(EntrenamientoModelo)
    total = (await db.execute(total_q)).scalar() or 0

    items = []
    for e in entrenamientos:
        f1_nuevo = None
        if e.metricas_nuevo and "f1_score" in e.metricas_nuevo:
            f1_nuevo = e.metricas_nuevo["f1_score"]
        f1_actual = None
        if e.metricas_actual and "f1_score" in e.metricas_actual:
            f1_actual = e.metricas_actual["f1_score"]

        items.append(EntrenamientoHistorialItem(
            id=e.id,
            fecha_inicio=e.fecha_inicio,
            fecha_fin=e.fecha_fin,
            estado=e.estado,
            nombre_archivo=e.nombre_archivo,
            total_registros=e.total_registros,
            tipo_mejor_modelo=e.tipo_mejor_modelo,
            f1_nuevo=f1_nuevo,
            f1_actual=f1_actual,
            usuario_nombre=e.usuario.nombre,
            version_generada=e.version_generada,
        ))

    return EntrenamientoHistorialResponse(total=total, entrenamientos=items)


# ------------------------------------------------------------------
# GET /entrenamiento/plantilla
# ------------------------------------------------------------------
@router.get(
    "/plantilla",
    summary="Descargar plantilla Excel",
    description="Descarga un archivo Excel (.xlsx) con las columnas requeridas para entrenamiento.",
)
async def descargar_plantilla(
    _: Usuario = Depends(get_current_user),
):
    output = entrenamiento_service.generar_plantilla_excel()
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=plantilla_entrenamiento.xlsx"},
    )


# ------------------------------------------------------------------
# GET /entrenamiento/modelo-actual
# ------------------------------------------------------------------
@router.get(
    "/modelo-actual",
    response_model=ModeloActualResponse,
    summary="Información del modelo en producción",
)
async def modelo_actual(
    _: Usuario = Depends(get_current_user),
):
    info = entrenamiento_service.leer_modelo_actual_info(settings.ml_model_dir)

    if info and "mejor_metricas" in info:
        metricas = MetricasModelo(**info["mejor_metricas"])
        return ModeloActualResponse(
            version=info.get("version", "desconocida"),
            tipo_modelo=info.get("tipo_modelo", info.get("mejor_modelo", "desconocido")),
            metricas=metricas,
            n_features=info.get("n_features_ohe", len(info.get("feature_columns_ohe", []))),
            fecha_entrenamiento=info.get("timestamp"),
        )

    # Si no hay model_info.json, retornar métricas hardcoded del v3 actual
    return ModeloActualResponse(
        version="v3_iterative_imputer_ohe_rf",
        tipo_modelo="RandomForestClassifier",
        metricas=MetricasModelo(
            accuracy=0.9329,
            precision=0.6190,
            recall=0.8667,
            f1_score=0.7222,
            roc_auc=0.9249,
        ),
        n_features=23,
        fecha_entrenamiento=None,
    )
