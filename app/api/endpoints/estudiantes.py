"""Endpoints de estudiantes (tabla de sección con asistencia y riesgo)."""
from datetime import date
from io import BytesIO
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_user, require_module
from app.core.database import get_db
from app.models import (
    Area,
    Asistencia,
    Estudiante,
    GestionAcademica,
    Inscripcion,
    MallaCurricular,
    Materia,
    Prediccion,
    Semestre,
    Usuario,
)
from app.models.paralelo import Paralelo
from app.models.asistencia import EstadoAsistencia
from app.schemas.estudiante import (
    EstudianteSociodemograficoUpdate,
    EstudianteTablaItem,
    EstudianteTablaResponse,
    ImportacionErrorItem,
    ImportacionEstudiantesResponse,
    ImportacionResumen,
)

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

    # Última predicción ML por estudiante (patrón reutilizado de /predicciones/dashboard)
    subq_pred = (
        select(
            Prediccion.estudiante_id,
            func.max(Prediccion.id).label("max_id"),
        )
        .group_by(Prediccion.estudiante_id)
        .subquery()
    )
    q_preds = (
        select(Prediccion.estudiante_id, Prediccion.probabilidad_abandono, Prediccion.nivel_riesgo)
        .join(subq_pred, Prediccion.id == subq_pred.c.max_id)
    )
    res_preds = await db.execute(q_preds)
    preds_map: dict[int, tuple[float, str]] = {
        r.estudiante_id: (r.probabilidad_abandono, r.nivel_riesgo) for r in res_preds
    }

    items = []
    for e in estudiantes:
        presentes, total = filas_asis.get(e.id, (0, 0))
        porcentaje = round(100.0 * presentes / total, 1) if total else 0.0
        nombre_completo = f"{e.nombre} {e.apellido}".strip()
        # Carrera: usar nombre del área si está cargado (paralelo -> area)
        carrera = None
        if e.paralelo and e.paralelo.area:
            carrera = e.paralelo.area.nombre

        # Predicción ML
        prob, nivel = preds_map.get(e.id, (None, None))
        clasificacion = None
        if prob is not None:
            clasificacion = "Abandona" if prob >= 0.5 else "No Abandona"

        items.append(
            EstudianteTablaItem(
                id=e.id,
                nombre_completo=nombre_completo,
                carrera=carrera,
                codigo_estudiante=e.codigo_estudiante,
                porcentaje_asistencia=porcentaje,
                nivel_riesgo=nivel,
                probabilidad_abandono=round(prob, 4) if prob is not None else None,
                clasificacion_abandono=clasificacion,
            )
        )

    return EstudianteTablaResponse(estudiantes=items)


# ── Campos sociodemográficos válidos para importación ────────────────

_CAMPOS_SOCIODEMOGRAFICOS = [
    "fecha_nacimiento", "genero", "grado", "estrato_socioeconomico",
    "ocupacion_laboral", "con_quien_vive", "apoyo_economico",
    "modalidad_ingreso", "tipo_colegio",
]

_COLUMNAS_OBLIGATORIAS = {"Codigo", "Nombre", "Apellido", "Area", "Paralelo"}


def _parse_materias(celda: str) -> list[str]:
    """Extrae nombres de materias de una celda separada por comas."""
    if not celda or not isinstance(celda, str) or pd.isna(celda):
        return []
    return [m.strip() for m in celda.split(",") if m.strip()]


def _val(row, col):
    """Devuelve el valor de la celda como string limpio, o None si está vacío/NaN."""
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s if s else None


@router.post(
    "/importar",
    response_model=ImportacionEstudiantesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Importar estudiantes desde Excel",
    description=(
        "Sube un archivo .xlsx con estudiantes. Crea/actualiza estudiantes, "
        "genera inscripciones y crea entidades catálogo (áreas, semestres, "
        "paralelos, materias) si no existen."
    ),
)
async def importar_estudiantes(
    archivo: UploadFile = File(..., description="Archivo Excel (.xlsx)"),
    db: AsyncSession = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    # ── Fase 0: Validación del archivo ──────────────────────────────
    nombre_archivo = archivo.filename or "sin_nombre"
    if not nombre_archivo.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe tener extensión .xlsx",
        )

    contenido = await archivo.read()
    try:
        df = pd.read_excel(BytesIO(contenido), engine="openpyxl")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo leer el archivo. Verifique que sea un Excel válido (.xlsx).",
        )

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo Excel está vacío.",
        )

    columnas_presentes = set(df.columns)
    faltantes = _COLUMNAS_OBLIGATORIAS - columnas_presentes
    if faltantes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Faltan columnas obligatorias: {', '.join(sorted(faltantes))}",
        )

    errores: list[ImportacionErrorItem] = []
    resumen = ImportacionResumen()
    estudiantes_creados = 0
    estudiantes_actualizados = 0

    # ── Fase 1: Pre-carga de entidades existentes ───────────────────

    # Áreas
    res = await db.execute(select(Area))
    areas_cache: dict[str, Area] = {a.nombre: a for a in res.scalars().all()}

    # Semestres
    res = await db.execute(select(Semestre))
    semestres_cache: dict[str, Semestre] = {s.nombre: s for s in res.scalars().all()}

    # Materias
    res = await db.execute(select(Materia))
    materias_cache: dict[str, Materia] = {m.nombre: m for m in res.scalars().all()}

    # Paralelos
    res = await db.execute(select(Paralelo))
    paralelos_cache: dict[tuple[str, int], Paralelo] = {
        (p.nombre, p.area_id): p for p in res.scalars().all()
    }

    # Gestiones académicas
    res = await db.execute(select(GestionAcademica))
    gestiones_cache: dict[str, GestionAcademica] = {
        g.nombre: g for g in res.scalars().all()
    }

    # Estudiantes
    res = await db.execute(select(Estudiante))
    estudiantes_cache: dict[str, Estudiante] = {
        e.codigo_estudiante: e for e in res.scalars().all()
    }

    # Malla curricular
    res = await db.execute(select(MallaCurricular))
    malla_cache: dict[tuple[int | None, int | None, int | None], MallaCurricular] = {
        (mc.materia_id, mc.area_id, mc.semestre_id): mc for mc in res.scalars().all()
    }

    # ── Fase 2: Pre-creación de entidades catálogo ──────────────────

    # 2.1 Áreas únicas
    areas_excel = {str(v).strip() for v in df["Area"].dropna().unique() if str(v).strip()}
    for nombre_area in areas_excel:
        if nombre_area not in areas_cache:
            area = Area(nombre=nombre_area)
            db.add(area)
            await db.flush()
            areas_cache[nombre_area] = area
            resumen.areas_creadas += 1

    # 2.2 Semestres únicos
    if "Semestre" in df.columns:
        semestres_excel = {
            str(v).strip() for v in df["Semestre"].dropna().unique() if str(v).strip()
        }
        for nombre_sem in semestres_excel:
            if nombre_sem not in semestres_cache:
                semestre = Semestre(nombre=nombre_sem)
                db.add(semestre)
                await db.flush()
                semestres_cache[nombre_sem] = semestre
                resumen.semestres_creados += 1

    # 2.3 Paralelos únicos (por nombre + área)
    paralelos_unicos: set[tuple[str, str]] = set()
    for _, row in df.iterrows():
        p_nombre = _val(row, "Paralelo")
        a_nombre = _val(row, "Area")
        if p_nombre and a_nombre:
            paralelos_unicos.add((p_nombre, a_nombre))

    for p_nombre, a_nombre in paralelos_unicos:
        area_obj = areas_cache.get(a_nombre)
        if not area_obj:
            continue
        # Resolver semestre_id si hay columna Semestre en alguna fila con este paralelo+area
        semestre_id = None
        if "Semestre" in df.columns:
            filas_match = df[(df["Paralelo"].astype(str).str.strip() == p_nombre) &
                            (df["Area"].astype(str).str.strip() == a_nombre)]
            for _, r in filas_match.iterrows():
                sem_nombre = _val(r, "Semestre")
                if sem_nombre and sem_nombre in semestres_cache:
                    semestre_id = semestres_cache[sem_nombre].id
                    break

        key = (p_nombre, area_obj.id)
        if key not in paralelos_cache:
            paralelo = Paralelo(
                nombre=p_nombre,
                area_id=area_obj.id,
                semestre_id=semestre_id,
                encargado_id=usuario.id,
            )
            db.add(paralelo)
            await db.flush()
            paralelos_cache[key] = paralelo
            resumen.paralelos_creados += 1

    # 2.4 Materias únicas (extraídas de la columna Materias)
    if "Materias" in df.columns:
        todas_materias: set[str] = set()
        for celda in df["Materias"].dropna().unique():
            todas_materias.update(_parse_materias(str(celda)))
        for nombre_mat in todas_materias:
            if nombre_mat not in materias_cache:
                materia = Materia(nombre=nombre_mat)
                db.add(materia)
                await db.flush()
                materias_cache[nombre_mat] = materia
                resumen.materias_creadas += 1

    # ── Fase 3: Procesamiento fila por fila ─────────────────────────

    for idx, row in df.iterrows():
        fila_num = int(idx) + 2  # +2: encabezado + 0-indexed

        codigo = _val(row, "Codigo")
        nombre = _val(row, "Nombre")
        apellido = _val(row, "Apellido")
        area_nombre = _val(row, "Area")
        paralelo_nombre = _val(row, "Paralelo")

        # Validar campos obligatorios
        campos_faltantes = []
        if not codigo:
            campos_faltantes.append("Codigo")
        if not nombre:
            campos_faltantes.append("Nombre")
        if not apellido:
            campos_faltantes.append("Apellido")
        if not area_nombre:
            campos_faltantes.append("Area")
        if not paralelo_nombre:
            campos_faltantes.append("Paralelo")

        if campos_faltantes:
            errores.append(ImportacionErrorItem(
                fila=fila_num,
                codigo=codigo,
                mensaje=f"Faltan campos obligatorios: {', '.join(campos_faltantes)}",
            ))
            continue

        # Resolver paralelo
        area_obj = areas_cache.get(area_nombre)
        if not area_obj:
            errores.append(ImportacionErrorItem(
                fila=fila_num, codigo=codigo,
                mensaje=f"Área '{area_nombre}' no encontrada en cache (error interno)",
            ))
            continue

        paralelo_obj = paralelos_cache.get((paralelo_nombre, area_obj.id))
        if not paralelo_obj:
            errores.append(ImportacionErrorItem(
                fila=fila_num, codigo=codigo,
                mensaje=f"Paralelo '{paralelo_nombre}' no encontrado para área '{area_nombre}'",
            ))
            continue

        # Crear o actualizar estudiante
        try:
            if codigo in estudiantes_cache:
                # Actualizar existente
                est = estudiantes_cache[codigo]
                est.nombre = nombre
                est.apellido = apellido
                est.paralelo_id = paralelo_obj.id
                # Actualizar campos sociodemográficos sin sobreescribir con null
                for campo in _CAMPOS_SOCIODEMOGRAFICOS:
                    if campo in df.columns:
                        valor = _val(row, campo)
                        if valor is not None:
                            if campo == "fecha_nacimiento":
                                try:
                                    valor = pd.to_datetime(valor).date()
                                except Exception:
                                    pass  # mantener valor actual si no se puede parsear
                                else:
                                    setattr(est, campo, valor)
                            else:
                                setattr(est, campo, valor)
                estudiantes_actualizados += 1
            else:
                # Crear nuevo
                kwargs: dict = {
                    "codigo_estudiante": codigo,
                    "nombre": nombre,
                    "apellido": apellido,
                    "paralelo_id": paralelo_obj.id,
                }
                for campo in _CAMPOS_SOCIODEMOGRAFICOS:
                    if campo in df.columns:
                        valor = _val(row, campo)
                        if valor is not None:
                            if campo == "fecha_nacimiento":
                                try:
                                    valor = pd.to_datetime(valor).date()
                                except Exception:
                                    valor = None
                            kwargs[campo] = valor
                est = Estudiante(**kwargs)
                db.add(est)
                await db.flush()
                estudiantes_cache[codigo] = est
                estudiantes_creados += 1
        except Exception as exc:
            errores.append(ImportacionErrorItem(
                fila=fila_num, codigo=codigo,
                mensaje=f"Error al crear/actualizar estudiante: {exc}",
            ))
            continue

        # Procesar materias e inscripciones
        materias_celda = _val(row, "Materias") if "Materias" in df.columns else None
        if not materias_celda:
            continue

        gestion_nombre = _val(row, "GestionAcademica") if "GestionAcademica" in df.columns else None
        if not gestion_nombre:
            errores.append(ImportacionErrorItem(
                fila=fila_num, codigo=codigo,
                mensaje="Tiene Materias pero falta GestionAcademica",
            ))
            continue

        gestion_obj = gestiones_cache.get(gestion_nombre)
        if not gestion_obj:
            errores.append(ImportacionErrorItem(
                fila=fila_num, codigo=codigo,
                mensaje=f"Gestión académica '{gestion_nombre}' no existe. Debe crearse previamente.",
            ))
            continue

        semestre_nombre = _val(row, "Semestre") if "Semestre" in df.columns else None
        semestre_obj = semestres_cache.get(semestre_nombre) if semestre_nombre else None

        nombres_materias = _parse_materias(materias_celda)
        for nombre_mat in nombres_materias:
            materia_obj = materias_cache.get(nombre_mat)
            if not materia_obj:
                errores.append(ImportacionErrorItem(
                    fila=fila_num, codigo=codigo,
                    mensaje=f"Materia '{nombre_mat}' no encontrada en cache (error interno)",
                ))
                continue

            # Malla curricular (usar savepoint para manejar duplicados UNIQUE)
            malla_key = (materia_obj.id, area_obj.id, semestre_obj.id if semestre_obj else None)
            if malla_key not in malla_cache:
                try:
                    nested_mc = await db.begin_nested()
                    mc = MallaCurricular(
                        materia_id=materia_obj.id,
                        area_id=area_obj.id,
                        semestre_id=semestre_obj.id if semestre_obj else None,
                    )
                    db.add(mc)
                    await db.flush()
                    malla_cache[malla_key] = mc
                    resumen.mallas_creadas += 1
                except Exception:
                    await nested_mc.rollback()

            # Inscripción (usar savepoint para manejar duplicados UNIQUE)
            try:
                nested = await db.begin_nested()
                insc = Inscripcion(
                    estudiante_id=est.id,
                    materia_id=materia_obj.id,
                    gestion_academica=gestion_nombre,
                    gestion_id=gestion_obj.id,
                )
                db.add(insc)
                await db.flush()
                resumen.inscripciones_creadas += 1
            except Exception:
                await nested.rollback()
                resumen.inscripciones_existentes += 1

    await db.commit()

    return ImportacionEstudiantesResponse(
        nombre_archivo=nombre_archivo,
        total_filas=len(df),
        estudiantes_creados=estudiantes_creados,
        estudiantes_actualizados=estudiantes_actualizados,
        total_errores=len(errores),
        errores=errores,
        resumen=resumen,
    )
