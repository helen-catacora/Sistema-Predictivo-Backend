"""Endpoints de predicciones de abandono (masiva, individual, historial, lotes, dashboard)."""
import math
from datetime import date
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import require_module
from app.core.database import get_db
from app.models import (
    Accion,
    Alerta,
    Area,
    Estudiante,
    LotePrediccion,
    NivelRiesgo,
    Paralelo,
    Prediccion,
    Semestre,
    Usuario,
)
from app.schemas.prediccion import (
    AccionItem,
    DashboardResponse,
    DistribucionParaleloItem,
    DistribucionRiesgoItem,
    EstudianteEvolucionResponse,
    EvolucionItem,
    LoteDetalleResponse,
    LotePrediccionItem,
    LotePrediccionListResponse,
    PrediccionHistorialItem,
    PrediccionHistorialResponse,
    PrediccionIndividualRequest,
    PrediccionIndividualResponse,
    ResumenGeneral,
)
from app.services import alerta_service
from app.services.prediccion_service import PrediccionService

router = APIRouter(prefix="/predicciones", tags=["predicciones"])


def get_prediccion_service(request: Request) -> PrediccionService:
    """Dependency: obtiene el servicio ML desde app.state."""
    svc = request.app.state.prediccion_service
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo ML no disponible. Verifique que los artefactos .pkl estén en el directorio configurado.",
        )
    return svc


# ------------------------------------------------------------------
# POST /predicciones/individual
# ------------------------------------------------------------------
@router.post(
    "/individual",
    response_model=PrediccionIndividualResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Predicción individual",
    description="Genera la predicción de abandono para un estudiante específico.",
)
async def prediccion_individual(
    body: PrediccionIndividualRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_module("Visualización de Resultados")),
    ml: PrediccionService = Depends(get_prediccion_service),
):
    # Buscar estudiante con su paralelo → semestre y área
    q = (
        select(Estudiante)
        .options(
            selectinload(Estudiante.paralelo)
            .selectinload(Paralelo.area),
            selectinload(Estudiante.paralelo)
            .selectinload(Paralelo.semestre),
        )
        .where(Estudiante.id == body.estudiante_id)
    )
    result = await db.execute(q)
    estudiante = result.scalar_one_or_none()
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    # Armar features
    features = _armar_features(estudiante, body.datos_academicos, body.datos_sociodemograficos)

    # Predecir
    probabilidad, nivel_riesgo = ml.predecir(features)

    # Guardar predicción
    prediccion = Prediccion(
        probabilidad_abandono=probabilidad,
        nivel_riesgo=nivel_riesgo,
        fecha_prediccion=date.today(),
        estudiante_id=estudiante.id,
        tipo="individual",
        features_utilizadas=features,
        version_modelo=PrediccionService.VERSION,
    )
    db.add(prediccion)
    await db.flush()

    # Generar alerta si corresponde
    alerta = await alerta_service.generar_alertas_prediccion(
        estudiante.id, prediccion.id, nivel_riesgo, probabilidad, db
    )

    nombre = f"{estudiante.nombre} {estudiante.apellido}".strip()
    return PrediccionIndividualResponse(
        prediccion_id=prediccion.id,
        estudiante_id=estudiante.id,
        nombre_estudiante=nombre,
        probabilidad_abandono=probabilidad,
        nivel_riesgo=nivel_riesgo,
        fecha_prediccion=prediccion.fecha_prediccion,
        features_utilizadas=features,
        alerta_generada=alerta is not None,
    )


# ------------------------------------------------------------------
# POST /predicciones/masiva
# ------------------------------------------------------------------
@router.post(
    "/masiva",
    status_code=status.HTTP_201_CREATED,
    summary="Predicción masiva (Excel)",
    description="Sube un archivo Excel (.xlsx) y genera predicciones para todos los estudiantes.",
)
async def prediccion_masiva(
    archivo: UploadFile = File(..., description="Archivo Excel (.xlsx)"),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_module("Visualización de Resultados")),
    ml: PrediccionService = Depends(get_prediccion_service),
    gestion_id: Annotated[int | None, Query(description="ID de la gestión académica")] = None,
):
    if not archivo.filename or not archivo.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .xlsx")

    # Leer Excel
    try:
        contents = await archivo.read()
        df = pd.read_excel(contents, engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer el archivo: {e}")

    if "Codigo" not in df.columns:
        raise HTTPException(status_code=400, detail="El archivo debe tener una columna 'Codigo'")

    # Crear lote
    lote = LotePrediccion(
        nombre_archivo=archivo.filename,
        usuario_id=current_user.id,
        gestion_id=gestion_id,
        estado="procesando",
        total_estudiantes=len(df),
        version_modelo=PrediccionService.VERSION,
    )
    db.add(lote)
    await db.flush()

    # Buscar todos los estudiantes con sus paralelos
    codigos = df["Codigo"].dropna().astype(str).tolist()
    q = (
        select(Estudiante)
        .options(
            selectinload(Estudiante.paralelo).selectinload(Paralelo.area),
            selectinload(Estudiante.paralelo).selectinload(Paralelo.semestre),
        )
        .where(Estudiante.codigo_estudiante.in_(codigos))
    )
    result = await db.execute(q)
    estudiantes_map = {e.codigo_estudiante: e for e in result.scalars().unique().all()}

    contadores = {"Bajo": 0, "Medio": 0, "Alto": 0, "Critico": 0}
    procesados = 0
    errores = []

    for _, row in df.iterrows():
        codigo = str(row.get("Codigo", "")).strip()
        estudiante = estudiantes_map.get(codigo)
        if not estudiante:
            errores.append(f"Estudiante no encontrado: {codigo}")
            continue

        # Actualizar datos sociodemográficos del estudiante desde el Excel
        _actualizar_estudiante_desde_excel(estudiante, row)

        # Armar features desde el Excel
        features = _armar_features_desde_excel(estudiante, row)

        try:
            probabilidad, nivel_riesgo = ml.predecir(features)
        except Exception:
            errores.append(f"Error al predecir: {codigo}")
            continue

        prediccion = Prediccion(
            probabilidad_abandono=probabilidad,
            nivel_riesgo=nivel_riesgo,
            fecha_prediccion=date.today(),
            estudiante_id=estudiante.id,
            lote_id=lote.id,
            gestion_id=gestion_id,
            tipo="masiva",
            features_utilizadas=features,
            version_modelo=PrediccionService.VERSION,
        )
        db.add(prediccion)
        await db.flush()

        # Generar alerta si corresponde
        await alerta_service.generar_alertas_prediccion(
            estudiante.id, prediccion.id, nivel_riesgo, probabilidad, db
        )

        contadores[nivel_riesgo] = contadores.get(nivel_riesgo, 0) + 1
        procesados += 1

    # Actualizar lote
    lote.estado = "completado"
    lote.total_procesados = procesados
    lote.total_bajo_riesgo = contadores["Bajo"]
    lote.total_medio_riesgo = contadores["Medio"]
    lote.total_alto_riesgo = contadores["Alto"]
    lote.total_critico = contadores["Critico"]
    if errores:
        lote.mensaje_error = "; ".join(errores[:20])

    return {
        "lote_id": lote.id,
        "nombre_archivo": lote.nombre_archivo,
        "estado": lote.estado,
        "total_estudiantes": lote.total_estudiantes,
        "total_procesados": procesados,
        "total_alto_riesgo": contadores["Alto"],
        "total_critico": contadores["Critico"],
        "errores": errores[:20] if errores else [],
    }


# ------------------------------------------------------------------
# GET /predicciones/historial
# ------------------------------------------------------------------
@router.get(
    "/historial",
    response_model=PrediccionHistorialResponse,
    summary="Historial de predicciones",
    description="Historial paginado con filtros opcionales.",
)
async def historial_predicciones(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Visualización de Resultados")),
    estudiante_id: Annotated[int | None, Query(description="Filtrar por estudiante")] = None,
    nivel_riesgo: Annotated[str | None, Query(description="Filtrar por nivel")] = None,
    tipo: Annotated[str | None, Query(description="individual o masiva")] = None,
    fecha_desde: Annotated[date | None, Query(description="Fecha desde")] = None,
    fecha_hasta: Annotated[date | None, Query(description="Fecha hasta")] = None,
    page: Annotated[int, Query(ge=1, description="Página")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Tamaño de página")] = 20,
):
    q = (
        select(Prediccion)
        .options(selectinload(Prediccion.estudiante))
        .order_by(Prediccion.fecha_prediccion.desc(), Prediccion.id.desc())
    )

    if estudiante_id:
        q = q.where(Prediccion.estudiante_id == estudiante_id)
    if nivel_riesgo:
        q = q.where(Prediccion.nivel_riesgo == nivel_riesgo)
    if tipo:
        q = q.where(Prediccion.tipo == tipo)
    if fecha_desde:
        q = q.where(Prediccion.fecha_prediccion >= fecha_desde)
    if fecha_hasta:
        q = q.where(Prediccion.fecha_prediccion <= fecha_hasta)

    # Count total
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginar
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    predicciones = result.scalars().unique().all()

    items = []
    for p in predicciones:
        e = p.estudiante
        items.append(PrediccionHistorialItem(
            id=p.id,
            estudiante_id=e.id,
            nombre_estudiante=f"{e.nombre} {e.apellido}".strip(),
            codigo_estudiante=e.codigo_estudiante,
            probabilidad_abandono=p.probabilidad_abandono,
            nivel_riesgo=p.nivel_riesgo,
            fecha_prediccion=p.fecha_prediccion,
            tipo=p.tipo,
            lote_id=p.lote_id,
            version_modelo=p.version_modelo,
        ))

    return PrediccionHistorialResponse(
        total=total,
        pagina=page,
        total_paginas=max(1, math.ceil(total / page_size)),
        predicciones=items,
    )


# ------------------------------------------------------------------
# GET /predicciones/historial/{estudiante_id}
# ------------------------------------------------------------------
@router.get(
    "/historial/{estudiante_id}",
    response_model=EstudianteEvolucionResponse,
    summary="Evolución de un estudiante",
    description="Historial de predicciones y datos de un estudiante específico.",
)
async def evolucion_estudiante(
    estudiante_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Visualización de Resultados")),
):
    # Estudiante
    q = select(Estudiante).where(Estudiante.id == estudiante_id)
    result = await db.execute(q)
    estudiante = result.scalar_one_or_none()
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    # Predicciones ordenadas por fecha
    q_pred = (
        select(Prediccion)
        .where(Prediccion.estudiante_id == estudiante_id)
        .order_by(Prediccion.fecha_prediccion.asc())
    )
    result = await db.execute(q_pred)
    predicciones = result.scalars().all()

    evolucion = [
        EvolucionItem(
            fecha=p.fecha_prediccion,
            probabilidad=p.probabilidad_abandono,
            nivel=p.nivel_riesgo,
        )
        for p in predicciones
    ]

    prediccion_actual = evolucion[-1] if evolucion else None

    # Acciones tomadas
    pred_ids = [p.id for p in predicciones]
    acciones = []
    if pred_ids:
        q_acc = (
            select(Accion)
            .where(Accion.prediccion_id.in_(pred_ids))
            .order_by(Accion.fecha.desc())
        )
        result = await db.execute(q_acc)
        acciones = [
            AccionItem(id=a.id, descripcion=a.descripcion, fecha=a.fecha)
            for a in result.scalars().all()
        ]

    # Datos sociodemográficos
    socio = {}
    for campo in [
        "fecha_nacimiento", "genero", "grado", "estrato_socioeconomico",
        "ocupacion_laboral", "con_quien_vive", "apoyo_economico",
        "modalidad_ingreso", "tipo_colegio",
    ]:
        val = getattr(estudiante, campo, None)
        if val is not None:
            socio[campo] = str(val)

    nombre = f"{estudiante.nombre} {estudiante.apellido}".strip()
    return EstudianteEvolucionResponse(
        estudiante_id=estudiante.id,
        nombre_estudiante=nombre,
        codigo_estudiante=estudiante.codigo_estudiante,
        prediccion_actual=prediccion_actual,
        evolucion=evolucion,
        datos_sociodemograficos=socio or None,
        acciones_tomadas=acciones,
    )


# ------------------------------------------------------------------
# GET /predicciones/lotes
# ------------------------------------------------------------------
@router.get(
    "/lotes",
    response_model=LotePrediccionListResponse,
    summary="Listar lotes de predicción",
)
async def listar_lotes(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Visualización de Resultados")),
):
    q = (
        select(LotePrediccion)
        .options(selectinload(LotePrediccion.usuario))
        .order_by(LotePrediccion.fecha_carga.desc())
    )
    result = await db.execute(q)
    lotes = result.scalars().unique().all()

    items = [
        LotePrediccionItem(
            id=l.id,
            nombre_archivo=l.nombre_archivo,
            fecha_carga=l.fecha_carga,
            usuario_nombre=l.usuario.nombre,
            estado=l.estado,
            total_estudiantes=l.total_estudiantes,
            total_procesados=l.total_procesados,
            total_alto_riesgo=l.total_alto_riesgo,
            total_critico=l.total_critico,
            version_modelo=l.version_modelo,
        )
        for l in lotes
    ]
    return LotePrediccionListResponse(lotes=items)


# ------------------------------------------------------------------
# GET /predicciones/lotes/{lote_id}
# ------------------------------------------------------------------
@router.get(
    "/lotes/{lote_id}",
    response_model=LoteDetalleResponse,
    summary="Detalle de un lote",
)
async def detalle_lote(
    lote_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Visualización de Resultados")),
):
    q = (
        select(LotePrediccion)
        .options(
            selectinload(LotePrediccion.usuario),
            selectinload(LotePrediccion.predicciones).selectinload(Prediccion.estudiante),
        )
        .where(LotePrediccion.id == lote_id)
    )
    result = await db.execute(q)
    lote = result.scalar_one_or_none()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    preds = [
        PrediccionHistorialItem(
            id=p.id,
            estudiante_id=p.estudiante.id,
            nombre_estudiante=f"{p.estudiante.nombre} {p.estudiante.apellido}".strip(),
            codigo_estudiante=p.estudiante.codigo_estudiante,
            probabilidad_abandono=p.probabilidad_abandono,
            nivel_riesgo=p.nivel_riesgo,
            fecha_prediccion=p.fecha_prediccion,
            tipo=p.tipo,
            lote_id=p.lote_id,
            version_modelo=p.version_modelo,
        )
        for p in lote.predicciones
    ]

    return LoteDetalleResponse(
        id=lote.id,
        nombre_archivo=lote.nombre_archivo,
        fecha_carga=lote.fecha_carga,
        usuario_nombre=lote.usuario.nombre,
        estado=lote.estado,
        total_estudiantes=lote.total_estudiantes,
        total_procesados=lote.total_procesados,
        total_alto_riesgo=lote.total_alto_riesgo,
        total_medio_riesgo=lote.total_medio_riesgo,
        total_bajo_riesgo=lote.total_bajo_riesgo,
        total_critico=lote.total_critico,
        version_modelo=lote.version_modelo,
        predicciones=preds,
    )


# ------------------------------------------------------------------
# GET /predicciones/dashboard
# ------------------------------------------------------------------
@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Dashboard de predicciones",
    description="Estadísticas generales de predicciones y alertas.",
)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Visualización de Resultados")),
    paralelo_id: Annotated[int | None, Query(description="Filtrar por paralelo")] = None,
):
    # Subquery: última predicción por estudiante
    subq = (
        select(
            Prediccion.estudiante_id,
            func.max(Prediccion.id).label("max_id"),
        )
        .group_by(Prediccion.estudiante_id)
        .subquery()
    )

    q_latest = (
        select(Prediccion)
        .options(
            selectinload(Prediccion.estudiante)
            .selectinload(Estudiante.paralelo)
            .selectinload(Paralelo.area),
        )
        .join(subq, Prediccion.id == subq.c.max_id)
    )

    if paralelo_id:
        q_latest = q_latest.where(Prediccion.estudiante.has(Estudiante.paralelo_id == paralelo_id))

    result = await db.execute(q_latest)
    latest_preds = result.scalars().unique().all()

    # Conteos por nivel
    niveles = {"Bajo": 0, "Medio": 0, "Alto": 0, "Critico": 0}
    por_paralelo: dict[str, dict] = {}

    for p in latest_preds:
        niveles[p.nivel_riesgo] = niveles.get(p.nivel_riesgo, 0) + 1
        par = p.estudiante.paralelo
        key = par.nombre
        if key not in por_paralelo:
            por_paralelo[key] = {
                "paralelo": par.nombre,
                "area": par.area.nombre if par.area else "",
                "total": 0, "alto_riesgo": 0, "critico": 0,
            }
        por_paralelo[key]["total"] += 1
        if p.nivel_riesgo == NivelRiesgo.ALTO:
            por_paralelo[key]["alto_riesgo"] += 1
        elif p.nivel_riesgo == NivelRiesgo.CRITICO:
            por_paralelo[key]["critico"] += 1

    total_pred = sum(niveles.values())

    # Alertas activas
    q_alertas = select(func.count()).select_from(Alerta).where(Alerta.estado == "activa")
    total_alertas = (await db.execute(q_alertas)).scalar() or 0

    q_alertas_crit = (
        select(func.count()).select_from(Alerta)
        .where(Alerta.estado == "activa", Alerta.tipo == "critica")
    )
    total_alertas_crit = (await db.execute(q_alertas_crit)).scalar() or 0

    # Total estudiantes
    q_est = select(func.count()).select_from(Estudiante)
    if paralelo_id:
        q_est = q_est.where(Estudiante.paralelo_id == paralelo_id)
    total_est = (await db.execute(q_est)).scalar() or 0

    pct_alto = round((niveles["Alto"] + niveles["Critico"]) / total_pred * 100, 1) if total_pred else 0

    resumen = ResumenGeneral(
        total_estudiantes=total_est,
        total_predicciones_activas=total_pred,
        total_alto_riesgo=niveles["Alto"],
        total_critico=niveles["Critico"],
        total_medio_riesgo=niveles["Medio"],
        total_bajo_riesgo=niveles["Bajo"],
        porcentaje_alto_riesgo=pct_alto,
        total_alertas_activas=total_alertas,
        total_alertas_criticas=total_alertas_crit,
    )

    dist_riesgo = [
        DistribucionRiesgoItem(
            nivel=n,
            cantidad=c,
            porcentaje=round(c / total_pred * 100, 1) if total_pred else 0,
        )
        for n, c in niveles.items()
    ]

    dist_paralelo = [
        DistribucionParaleloItem(**v) for v in por_paralelo.values()
    ]

    return DashboardResponse(
        resumen_general=resumen,
        distribucion_riesgo=dist_riesgo,
        distribucion_por_paralelo=dist_paralelo,
    )


# ------------------------------------------------------------------
# Utilidades privadas
# ------------------------------------------------------------------
def _armar_features(estudiante, datos_acad, datos_socio=None) -> dict:
    """Arma el dict de features para el modelo ML."""
    # Datos académicos
    features: dict = {
        "Mat": datos_acad.materias_inscritas,
        "Rep": datos_acad.materias_reprobadas,
        "2T": datos_acad.materias_segunda_oportunidad,
        "Prom": datos_acad.promedio_general,
    }

    # Semestre y Carrera derivados del paralelo
    paralelo = estudiante.paralelo
    if paralelo and paralelo.semestre:
        features["Semestre"] = paralelo.semestre.nombre.split()[0] if paralelo.semestre.nombre else None
    if paralelo and paralelo.area:
        features["Carrera"] = paralelo.area.nombre

    # Datos sociodemográficos: prioridad al body, fallback a la BD
    if datos_socio:
        features["edad"] = datos_socio.edad
        features["Grado"] = datos_socio.grado
        features["Genero"] = datos_socio.genero
        features["estrato_socioeconomico"] = datos_socio.estrato_socioeconomico
        features["ocupacion_laboral"] = datos_socio.ocupacion_laboral
        features["con_quien_vive"] = datos_socio.con_quien_vive
        features["apoyo_economico"] = datos_socio.apoyo_economico
        features["modalidad_ingreso"] = datos_socio.modalidad_ingreso
        features["tipo_colegio"] = datos_socio.tipo_colegio
    else:
        # Tomar de la BD
        if estudiante.fecha_nacimiento:
            features["edad"] = date.today().year - estudiante.fecha_nacimiento.year
        else:
            features["edad"] = None
        features["Grado"] = estudiante.grado
        features["Genero"] = estudiante.genero
        features["estrato_socioeconomico"] = estudiante.estrato_socioeconomico
        features["ocupacion_laboral"] = estudiante.ocupacion_laboral
        features["con_quien_vive"] = estudiante.con_quien_vive
        features["apoyo_economico"] = estudiante.apoyo_economico
        features["modalidad_ingreso"] = estudiante.modalidad_ingreso
        features["tipo_colegio"] = estudiante.tipo_colegio

    return features


def _actualizar_estudiante_desde_excel(estudiante, row) -> None:
    """Actualiza los datos sociodemográficos del estudiante con los valores del Excel.

    Solo sobreescribe si el valor del Excel no es nulo/vacío.
    """
    # Mapeo: columna Excel → atributo del modelo Estudiante
    campos_socio = {
        "Grado": "grado",
        "Genero": "genero",
        "estrato_socioeconomico": "estrato_socioeconomico",
        "ocupacion_laboral": "ocupacion_laboral",
        "con_quien_vive": "con_quien_vive",
        "apoyo_economico": "apoyo_economico",
        "modalidad_ingreso": "modalidad_ingreso",
        "tipo_colegio": "tipo_colegio",
    }
    for col_excel, attr in campos_socio.items():
        val = row.get(col_excel)
        if val is not None and not (isinstance(val, float) and pd.isna(val)):
            val_str = str(val).strip()
            if val_str:
                setattr(estudiante, attr, val_str)

    # Edad → fecha_nacimiento (si viene edad y no tiene fecha_nacimiento)
    edad_val = row.get("edad")
    if edad_val is not None and not (isinstance(edad_val, float) and pd.isna(edad_val)):
        if estudiante.fecha_nacimiento is None:
            try:
                edad_int = int(edad_val)
                estudiante.fecha_nacimiento = date(date.today().year - edad_int, 1, 1)
            except (ValueError, TypeError):
                pass


def _armar_features_desde_excel(estudiante, row) -> dict:
    """Arma features desde una fila del DataFrame Excel."""
    features: dict = {}

    # Numéricas del Excel
    for col_excel, col_model in [("Mat", "Mat"), ("Rep", "Rep"), ("2T", "2T"), ("Prom", "Prom"), ("edad", "edad")]:
        val = row.get(col_excel)
        features[col_model] = None if pd.isna(val) else val

    # Semestre y Carrera del paralelo
    paralelo = estudiante.paralelo
    if paralelo and paralelo.semestre:
        features["Semestre"] = paralelo.semestre.nombre.split()[0] if paralelo.semestre.nombre else None
    if paralelo and paralelo.area:
        features["Carrera"] = paralelo.area.nombre

    # Sociodemográficas: Excel tiene prioridad, luego BD
    socio_cols = [
        "Grado", "Genero", "estrato_socioeconomico", "ocupacion_laboral",
        "con_quien_vive", "apoyo_economico", "modalidad_ingreso", "tipo_colegio",
    ]
    for col in socio_cols:
        val = row.get(col)
        if val is not None and not (isinstance(val, float) and pd.isna(val)):
            features[col] = val
        else:
            features[col] = getattr(estudiante, col.lower() if col[0].isupper() else col, None)

    # Edad: del Excel o de la BD
    if features.get("edad") is None and estudiante.fecha_nacimiento:
        features["edad"] = date.today().year - estudiante.fecha_nacimiento.year

    return features
