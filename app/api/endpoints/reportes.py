"""Endpoints de generación de reportes PDF."""
import math
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models import (
    Accion,
    Alerta,
    Area,
    Asistencia,
    Estudiante,
    MallaCurricular,
    Materia,
    NivelRiesgo,
    Paralelo,
    Prediccion,
    ReporteGenerado,
    Semestre,
    Usuario,
)
from app.schemas.reporte import (
    ReporteGeneradoItem,
    ReporteGenerarRequest,
    ReportesListResponse,
    TipoReporteInfo,
    TiposReporteResponse,
)
from app.services import reporte_pdf_service

router = APIRouter(prefix="/reportes", tags=["reportes"])

TIPOS_INFO = [
    TipoReporteInfo(
        tipo="predictivo_general",
        nombre="Reporte Predictivo General",
        descripcion="Resumen ejecutivo: distribución de riesgo, métricas globales y distribución por paralelo.",
    ),
    TipoReporteInfo(
        tipo="estudiantes_riesgo",
        nombre="Estudiantes en Riesgo",
        descripcion="Listado de estudiantes con nivel de riesgo Alto o Critico.",
    ),
    TipoReporteInfo(
        tipo="por_paralelo",
        nombre="Reporte por Paralelo",
        descripcion="Análisis desglosado de un paralelo: estudiantes, riesgo y asistencia.",
        requiere_paralelo=True,
    ),
    TipoReporteInfo(
        tipo="asistencia",
        nombre="Reporte de Asistencia",
        descripcion="Resumen de asistencia por materia, opcionalmente filtrado por paralelo.",
    ),
    TipoReporteInfo(
        tipo="individual",
        nombre="Reporte Individual",
        descripcion="Ficha completa de un estudiante: datos personales, predicciones, alertas y acciones.",
        requiere_estudiante=True,
    ),
]


# ------------------------------------------------------------------
# GET /reportes/tipos
# ------------------------------------------------------------------
@router.get(
    "/tipos",
    response_model=TiposReporteResponse,
    summary="Tipos de reporte disponibles",
)
async def listar_tipos(
    _: Usuario = Depends(get_current_user),
):
    return TiposReporteResponse(tipos=TIPOS_INFO)


# ------------------------------------------------------------------
# GET /reportes/historial
# ------------------------------------------------------------------
@router.get(
    "/historial",
    response_model=ReportesListResponse,
    summary="Historial de reportes generados",
)
async def historial_reportes(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    q = (
        select(ReporteGenerado)
        .options(selectinload(ReporteGenerado.generado_por))
        .order_by(ReporteGenerado.fecha_generacion.desc())
    )

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    reportes = result.scalars().unique().all()

    items = [
        ReporteGeneradoItem(
            id=r.id,
            tipo=r.tipo,
            nombre=r.nombre,
            generado_por_nombre=r.generado_por.nombre,
            fecha_generacion=r.fecha_generacion,
            parametros=r.parametros,
        )
        for r in reportes
    ]

    return ReportesListResponse(total=total, reportes=items)


# ------------------------------------------------------------------
# POST /reportes/generar
# ------------------------------------------------------------------
@router.post(
    "/generar",
    summary="Generar reporte PDF",
    description="Genera un PDF según el tipo solicitado y lo devuelve como descarga directa.",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "Archivo PDF generado"},
        400: {"description": "Parámetros inválidos para el tipo de reporte"},
    },
)
async def generar_reporte(
    body: ReporteGenerarRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if body.tipo == "por_paralelo" and not body.paralelo_id:
        raise HTTPException(status_code=400, detail="paralelo_id es requerido para el reporte por_paralelo")
    if body.tipo == "individual" and not body.estudiante_id:
        raise HTTPException(status_code=400, detail="estudiante_id es requerido para el reporte individual")

    usuario_nombre = current_user.nombre
    svc = getattr(request.app.state, "prediccion_service", None)

    if body.tipo == "predictivo_general":
        pdf_bytes, nombre = await _generar_predictivo_general(db, body, usuario_nombre, svc)
    elif body.tipo == "estudiantes_riesgo":
        pdf_bytes, nombre = await _generar_estudiantes_riesgo(db, body, usuario_nombre, svc)
    elif body.tipo == "por_paralelo":
        pdf_bytes, nombre = await _generar_por_paralelo(db, body, usuario_nombre, svc)
    elif body.tipo == "asistencia":
        pdf_bytes, nombre = await _generar_asistencia(db, body, usuario_nombre)
    elif body.tipo == "individual":
        pdf_bytes, nombre = await _generar_individual(db, body, usuario_nombre, svc)
    else:
        raise HTTPException(status_code=400, detail="Tipo de reporte no válido")

    registro = ReporteGenerado(
        tipo=body.tipo,
        nombre=nombre,
        generado_por_id=current_user.id,
        parametros=body.model_dump(exclude_none=True, exclude={"tipo"}),
    )
    db.add(registro)
    await db.commit()

    from datetime import date as _date
    fecha_str = _date.today().strftime("%Y-%m-%d")
    filename = f"{body.tipo}_{fecha_str}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==================================================================
# Funciones internas para cada tipo de reporte
# ==================================================================

async def _generar_predictivo_general(db: AsyncSession, body: ReporteGenerarRequest, usuario_nombre: str = "", svc=None) -> tuple[bytes, str]:
    """Reporte predictivo general: resumen + distribución riesgo + distribución paralelo."""
    # Subquery: última predicción por estudiante (por fecha_prediccion DESC, id DESC)
    subq = (
        select(
            Prediccion.id.label("pred_id"),
            Prediccion.estudiante_id,
            func.row_number()
            .over(
                partition_by=Prediccion.estudiante_id,
                order_by=[Prediccion.fecha_prediccion.desc(), Prediccion.id.desc()],
            )
            .label("rn"),
        )
        .subquery()
    )

    q_latest = (
        select(Prediccion)
        .options(
            selectinload(Prediccion.estudiante)
            .selectinload(Estudiante.paralelo)
            .selectinload(Paralelo.area),
        )
        .join(subq, Prediccion.id == subq.c.pred_id)
        .where(subq.c.rn == 1)
    )

    result = await db.execute(q_latest)
    latest_preds = result.scalars().unique().all()

    # Conteos
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

    # Alertas
    q_alertas = select(func.count()).select_from(Alerta).where(Alerta.estado == "activa")
    total_alertas = (await db.execute(q_alertas)).scalar() or 0
    q_alertas_crit = select(func.count()).select_from(Alerta).where(
        Alerta.estado == "activa", Alerta.tipo == "critica"
    )
    total_alertas_crit = (await db.execute(q_alertas_crit)).scalar() or 0

    # Total estudiantes
    total_est = (await db.execute(select(func.count()).select_from(Estudiante))).scalar() or 0

    pct_alto = round((niveles["Alto"] + niveles["Critico"]) / total_pred * 100, 1) if total_pred else 0

    resumen = {
        "total_estudiantes": total_est,
        "total_predicciones_activas": total_pred,
        "total_alto_riesgo": niveles["Alto"],
        "total_critico": niveles["Critico"],
        "total_medio_riesgo": niveles["Medio"],
        "total_bajo_riesgo": niveles["Bajo"],
        "porcentaje_alto_riesgo": pct_alto,
        "total_alertas_activas": total_alertas,
        "total_alertas_criticas": total_alertas_crit,
    }

    dist_riesgo = [
        {"nivel": n, "cantidad": c, "porcentaje": round(c / total_pred * 100, 1) if total_pred else 0}
        for n, c in niveles.items()
    ]

    dist_paralelo = list(por_paralelo.values())

    importancias = svc.importancias_globales(top_n=8) if svc else []

    pdf = reporte_pdf_service.generar_predictivo_general(
        resumen, dist_riesgo, dist_paralelo,
        usuario_nombre=usuario_nombre,
        importancias_globales=importancias,
    )
    return pdf, "Reporte Predictivo General"


async def _generar_estudiantes_riesgo(db: AsyncSession, body: ReporteGenerarRequest, usuario_nombre: str = "", svc=None) -> tuple[bytes, str]:
    """Estudiantes con riesgo Alto o Critico."""
    # Subquery: última predicción por estudiante (por fecha_prediccion DESC, id DESC)
    subq = (
        select(
            Prediccion.id.label("pred_id"),
            Prediccion.estudiante_id,
            func.row_number()
            .over(
                partition_by=Prediccion.estudiante_id,
                order_by=[Prediccion.fecha_prediccion.desc(), Prediccion.id.desc()],
            )
            .label("rn"),
        )
        .subquery()
    )

    q = (
        select(Prediccion)
        .options(
            selectinload(Prediccion.estudiante)
            .selectinload(Estudiante.paralelo),
        )
        .join(subq, Prediccion.id == subq.c.pred_id)
        .where(subq.c.rn == 1)
        .where(Prediccion.nivel_riesgo.in_([NivelRiesgo.ALTO, NivelRiesgo.CRITICO]))
    )

    # Filtro opcional por nivel específico
    if body.nivel_riesgo:
        q = q.where(Prediccion.nivel_riesgo == body.nivel_riesgo)

    q = q.order_by(Prediccion.probabilidad_abandono.desc())
    result = await db.execute(q)
    preds = result.scalars().unique().all()

    estudiantes = []
    for p in preds:
        factores_top2 = []
        if svc and p.features_utilizadas:
            try:
                # top_n=15 para obtener todos los features agrupados; luego filtrar por tipo riesgo
                # (ordenar por |contribución| y tomar top-2 directamente fallaría si los 2 mayores son protectores)
                todos = svc.explicar_shap(p.features_utilizadas, top_n=15)
                riesgo = sorted([f for f in todos if f["tipo"] == "riesgo"], key=lambda x: -x["contribucion"])
                factores_top2 = [f["nombre"] for f in riesgo[:2]]
            except Exception as e:
                print(f"[SHAP] Error estudiante {p.estudiante.codigo_estudiante}: {e}", flush=True)
        estudiantes.append({
            "codigo_estudiante": p.estudiante.codigo_estudiante,
            "nombre_estudiante": f"{p.estudiante.nombre} {p.estudiante.apellido}".strip(),
            "paralelo": p.estudiante.paralelo.nombre if p.estudiante.paralelo else "",
            "probabilidad_abandono": p.probabilidad_abandono,
            "nivel_riesgo": p.nivel_riesgo,
            "fecha_prediccion": p.fecha_prediccion.strftime("%d/%m/%Y"),
            "factores_principales": ", ".join(factores_top2) if factores_top2 else "—",
        })

    # Total de estudiantes con predicción (para contexto interpretativo)
    subq_total = (
        select(
            Prediccion.estudiante_id,
            func.row_number()
            .over(
                partition_by=Prediccion.estudiante_id,
                order_by=[Prediccion.fecha_prediccion.desc(), Prediccion.id.desc()],
            )
            .label("rn"),
        )
        .subquery()
    )
    q_total = select(func.count()).select_from(subq_total).where(subq_total.c.rn == 1)
    total_con_prediccion = (await db.execute(q_total)).scalar() or 0

    pdf = reporte_pdf_service.generar_estudiantes_riesgo(
        estudiantes, usuario_nombre=usuario_nombre, total_con_prediccion=total_con_prediccion,
    )
    return pdf, "Estudiantes en Riesgo"


async def _generar_por_paralelo(db: AsyncSession, body: ReporteGenerarRequest, usuario_nombre: str = "", svc=None) -> tuple[bytes, str]:
    """Reporte desglosado por paralelo."""
    # Info del paralelo
    q_par = (
        select(Paralelo)
        .options(selectinload(Paralelo.area))
        .where(Paralelo.id == body.paralelo_id)
    )
    result = await db.execute(q_par)
    paralelo = result.scalar_one_or_none()
    if not paralelo:
        raise HTTPException(status_code=404, detail="Paralelo no encontrado")

    paralelo_info = {
        "nombre": paralelo.nombre,
        "area": paralelo.area.nombre if paralelo.area else "",
    }

    # Estudiantes del paralelo
    q_est = (
        select(Estudiante)
        .where(Estudiante.paralelo_id == body.paralelo_id)
        .order_by(Estudiante.apellido, Estudiante.nombre)
    )
    result = await db.execute(q_est)
    estudiantes_db = result.scalars().all()

    est_ids = [e.id for e in estudiantes_db]

    # Última predicción de cada estudiante (por fecha_prediccion DESC, id DESC)
    preds_map: dict[int, Prediccion] = {}
    if est_ids:
        subq = (
            select(
                Prediccion.id.label("pred_id"),
                Prediccion.estudiante_id,
                func.row_number()
                .over(
                    partition_by=Prediccion.estudiante_id,
                    order_by=[Prediccion.fecha_prediccion.desc(), Prediccion.id.desc()],
                )
                .label("rn"),
            )
            .where(Prediccion.estudiante_id.in_(est_ids))
            .subquery()
        )
        q_pred = select(Prediccion).join(subq, Prediccion.id == subq.c.pred_id).where(subq.c.rn == 1)
        result = await db.execute(q_pred)
        for p in result.scalars().all():
            preds_map[p.estudiante_id] = p

    # Porcentaje de asistencia por estudiante
    asist_map: dict[int, float] = {}
    if est_ids:
        q_asist = (
            select(
                Asistencia.estudiante_id,
                func.count().label("total"),
                func.count().filter(Asistencia.estado == "Presente").label("presentes"),
            )
            .where(Asistencia.estudiante_id.in_(est_ids))
            .group_by(Asistencia.estudiante_id)
        )
        result = await db.execute(q_asist)
        for row in result.all():
            total = row.total or 0
            presentes = row.presentes or 0
            asist_map[row.estudiante_id] = (presentes / total * 100) if total > 0 else 0

    # Armar lista de estudiantes
    estudiantes_lista = []
    for e in estudiantes_db:
        pred = preds_map.get(e.id)
        factores_str = "—"
        if svc and pred and pred.features_utilizadas and pred.nivel_riesgo in ("Alto", "Critico"):
            try:
                # top_n=15 para obtener todos los features agrupados; luego filtrar por tipo riesgo
                todos = svc.explicar_shap(pred.features_utilizadas, top_n=15)
                riesgo = sorted([f for f in todos if f["tipo"] == "riesgo"], key=lambda x: -x["contribucion"])
                nombres = [f["nombre"] for f in riesgo[:2]]
                factores_str = ", ".join(nombres) if nombres else "—"
            except Exception as e:
                print(f"[SHAP] Error estudiante {e}: {e}", flush=True)
        estudiantes_lista.append({
            "codigo_estudiante": e.codigo_estudiante,
            "nombre_completo": f"{e.nombre} {e.apellido}".strip(),
            "porcentaje_asistencia": asist_map.get(e.id, 0),
            "probabilidad": pred.probabilidad_abandono if pred else None,
            "nivel_riesgo": pred.nivel_riesgo if pred else "Sin prediccion",
            "factores_principales": factores_str,
        })

    pdf = reporte_pdf_service.generar_por_paralelo(paralelo_info, estudiantes_lista, usuario_nombre=usuario_nombre)
    return pdf, f"Reporte Paralelo {paralelo.nombre}"


async def _generar_asistencia(db: AsyncSession, body: ReporteGenerarRequest, usuario_nombre: str = "") -> tuple[bytes, str]:
    """Reporte de asistencia agrupado por semestre → paralelo → materia."""
    paralelo_nombre = None

    q = (
        select(
            func.coalesce(Semestre.nombre, "Sin Semestre").label("semestre"),
            Paralelo.id.label("paralelo_id"),
            Paralelo.nombre.label("paralelo"),
            Area.nombre.label("area"),
            Materia.nombre.label("materia"),
            func.count().label("total_clases"),
            func.count().filter(Asistencia.estado == "Presente").label("presentes"),
            func.count().filter(Asistencia.estado == "Ausente").label("ausentes"),
        )
        .join(Estudiante, Estudiante.id == Asistencia.estudiante_id)
        .join(Paralelo, Paralelo.id == Estudiante.paralelo_id)
        .outerjoin(Semestre, Semestre.id == Paralelo.semestre_id)
        .join(Area, Area.id == Paralelo.area_id)
        .join(Materia, Materia.id == Asistencia.materia_id)
        # Solo materias que pertenecen a la malla del area+semestre del paralelo
        .join(
            MallaCurricular,
            and_(
                MallaCurricular.materia_id == Materia.id,
                MallaCurricular.area_id == Paralelo.area_id,
                or_(
                    Paralelo.semestre_id == None,
                    MallaCurricular.semestre_id == Paralelo.semestre_id,
                ),
            ),
        )
    )

    if body.paralelo_id:
        q = q.where(Estudiante.paralelo_id == body.paralelo_id)
        result_par = await db.execute(
            select(Paralelo.nombre, Area.nombre.label("area_nombre"))
            .join(Area, Area.id == Paralelo.area_id)
            .where(Paralelo.id == body.paralelo_id)
        )
        row_par = result_par.one_or_none()
        if row_par:
            paralelo_nombre = f"{row_par.nombre} ({row_par.area_nombre})"

    q = q.group_by(
        Semestre.nombre,
        Paralelo.id,
        Paralelo.nombre,
        Area.nombre,
        Materia.nombre,
    ).order_by(
        func.coalesce(Semestre.nombre, "Sin Semestre"),
        Area.nombre,
        Paralelo.nombre,
        Materia.nombre,
    )

    result = await db.execute(q)

    grupos: dict[tuple, dict] = {}
    for row in result.all():
        key = (row.semestre, row.paralelo_id)
        if key not in grupos:
            grupos[key] = {
                "semestre": row.semestre,
                "paralelo": f"{row.paralelo} ({row.area})",
                "materias": [],
            }
        total = row.total_clases or 0
        presentes = row.presentes or 0
        ausentes = row.ausentes or 0
        pct = (presentes / total * 100) if total > 0 else 0
        grupos[key]["materias"].append({
            "materia": row.materia,
            "total_clases": total,
            "presentes": presentes,
            "ausentes": ausentes,
            "porcentaje_asistencia": pct,
        })

    grupos_lista = list(grupos.values())

    pdf = reporte_pdf_service.generar_asistencia(grupos_lista, paralelo_nombre, usuario_nombre=usuario_nombre)
    nombre = f"Reporte Asistencia {paralelo_nombre}" if paralelo_nombre else "Reporte Asistencia General"
    return pdf, nombre


async def _generar_individual(db: AsyncSession, body: ReporteGenerarRequest, usuario_nombre: str = "", svc=None) -> tuple[bytes, str]:
    """Reporte individual de un estudiante."""
    # Estudiante con paralelo
    q = (
        select(Estudiante)
        .options(selectinload(Estudiante.paralelo))
        .where(Estudiante.id == body.estudiante_id)
    )
    result = await db.execute(q)
    estudiante = result.scalar_one_or_none()
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    nombre_completo = f"{estudiante.nombre} {estudiante.apellido}".strip()

    # Porcentaje de asistencia
    q_asist = (
        select(
            func.count().label("total"),
            func.count().filter(Asistencia.estado == "Presente").label("presentes"),
        )
        .where(Asistencia.estudiante_id == estudiante.id)
    )
    result = await db.execute(q_asist)
    row = result.one()
    pct_asist = (row.presentes / row.total * 100) if row.total > 0 else 0

    # Calcular edad
    edad = None
    if estudiante.fecha_nacimiento:
        from datetime import date
        hoy = date.today()
        edad = hoy.year - estudiante.fecha_nacimiento.year
        if (hoy.month, hoy.day) < (estudiante.fecha_nacimiento.month, estudiante.fecha_nacimiento.day):
            edad -= 1

    est_data = {
        "codigo_estudiante": estudiante.codigo_estudiante,
        "nombre_completo": nombre_completo,
        "paralelo": estudiante.paralelo.nombre if estudiante.paralelo else "",
        "genero": estudiante.genero,
        "edad": edad,
        "grado": estudiante.grado,
        "estrato_socioeconomico": estudiante.estrato_socioeconomico,
        "ocupacion_laboral": estudiante.ocupacion_laboral,
        "con_quien_vive": estudiante.con_quien_vive,
        "apoyo_economico": estudiante.apoyo_economico,
        "modalidad_ingreso": estudiante.modalidad_ingreso,
        "tipo_colegio": estudiante.tipo_colegio,
        "porcentaje_asistencia": pct_asist,
    }

    # Predicciones
    q_pred = (
        select(Prediccion)
        .where(Prediccion.estudiante_id == estudiante.id)
        .order_by(Prediccion.fecha_prediccion.desc())
    )
    result = await db.execute(q_pred)
    predicciones = [
        {
            "fecha_prediccion": str(p.fecha_prediccion),
            "probabilidad_abandono": p.probabilidad_abandono,
            "nivel_riesgo": p.nivel_riesgo,
            "tipo": p.tipo,
            "features_utilizadas": p.features_utilizadas,
        }
        for p in result.scalars().all()
    ]

    # Alertas
    q_alertas = (
        select(Alerta)
        .where(Alerta.estudiante_id == estudiante.id)
        .order_by(Alerta.fecha_creacion.desc())
    )
    result = await db.execute(q_alertas)
    alertas = [
        {
            "tipo": a.tipo,
            "nivel": a.nivel,
            "titulo": a.titulo,
            "estado": a.estado,
            "fecha_creacion": str(a.fecha_creacion),
        }
        for a in result.scalars().all()
    ]

    # Acciones (desde predicciones del estudiante)
    pred_ids = list((await db.execute(
        select(Prediccion.id).where(Prediccion.estudiante_id == estudiante.id)
    )).scalars().all())

    acciones = []
    if pred_ids:
        q_acc = (
            select(Accion)
            .where(Accion.prediccion_id.in_(pred_ids))
            .order_by(Accion.fecha.desc())
        )
        result = await db.execute(q_acc)
        acciones = [
            {"fecha": str(a.fecha), "descripcion": a.descripcion}
            for a in result.scalars().all()
        ]

    shap_factores = []
    if svc and predicciones:
        feats = predicciones[0].get("features_utilizadas") or {}
        if feats:
            try:
                shap_factores = svc.explicar_shap(feats, top_n=5)
            except Exception:
                pass

    pdf = reporte_pdf_service.generar_individual(
        est_data, predicciones, alertas, acciones,
        usuario_nombre=usuario_nombre,
        shap_factores=shap_factores,
    )
    return pdf, f"Reporte Individual {nombre_completo}"
