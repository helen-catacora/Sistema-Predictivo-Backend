"""Endpoint para importar malla curricular desde Excel."""
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models import Area, MallaCurricular, Materia, Semestre
from app.models import Usuario
from app.schemas.malla_curricular import ImportacionMallaErrorItem, ImportacionMallaResponse

router = APIRouter(prefix="/malla-curricular", tags=["malla-curricular"])

_COLUMNAS_REQUERIDAS = {"Nombre Materia", "Area", "Semestre"}


def _val(row, col):
    """Devuelve el valor de la celda como string limpio, o None si está vacío/NaN."""
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s if s else None


@router.post(
    "/importar",
    response_model=ImportacionMallaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Importar malla curricular desde Excel",
    description=(
        "Sube un archivo .xlsx con la malla curricular. "
        "Columnas requeridas: 'Nombre Materia', 'Area', 'Semestre'. "
        "Las materias se crean si no existen; áreas y semestres deben existir previamente. "
        "Los registros duplicados (misma materia+área+semestre) son omitidos."
    ),
)
async def importar_malla_curricular(
    archivo: UploadFile = File(..., description="Archivo Excel (.xlsx)"),
    nombre_malla: str = Form(..., description="Nombre de la malla curricular (ej. 'Competencias 2024-2028')"),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
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
        df.columns = df.columns.str.strip()
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

    faltantes = _COLUMNAS_REQUERIDAS - set(df.columns)
    if faltantes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Faltan columnas requeridas: {', '.join(sorted(faltantes))}",
        )

    errores: list[ImportacionMallaErrorItem] = []
    registros_creados = 0
    materias_creadas = 0
    ya_existentes = 0

    # ── Fase 1: Pre-carga de catálogos ──────────────────────────────

    res = await db.execute(select(Area))
    areas_cache: dict[str, Area] = {a.nombre: a for a in res.scalars().all()}

    res = await db.execute(select(Semestre))
    semestres_cache: dict[str, Semestre] = {s.nombre: s for s in res.scalars().all()}

    res = await db.execute(select(Materia))
    materias_cache: dict[str, Materia] = {m.nombre: m for m in res.scalars().all()}

    res = await db.execute(select(MallaCurricular))
    malla_cache: dict[tuple[int, int, int, str | None], MallaCurricular] = {
        (mc.materia_id, mc.area_id, mc.semestre_id, mc.nombre_malla): mc
        for mc in res.scalars().all()
        if mc.materia_id is not None and mc.area_id is not None and mc.semestre_id is not None
    }

    # ── Fase 2: Pre-creación de materias nuevas ──────────────────────
    nombres_materias = {
        str(v).strip()
        for v in df["Nombre Materia"].dropna().unique()
        if str(v).strip()
    }
    for nombre_materia in nombres_materias:
        if nombre_materia not in materias_cache:
            nueva_materia = Materia(nombre=nombre_materia)
            db.add(nueva_materia)
            await db.flush()
            materias_cache[nombre_materia] = nueva_materia
            materias_creadas += 1

    # ── Fase 3: Fila por fila ────────────────────────────────────────
    for idx, row in df.iterrows():
        fila_num = int(idx) + 2  # +2 porque idx es 0-based y la fila 1 es el encabezado

        nombre_materia = _val(row, "Nombre Materia")
        nombre_area = _val(row, "Area")
        nombre_semestre = _val(row, "Semestre")

        if not nombre_materia:
            errores.append(ImportacionMallaErrorItem(fila=fila_num, detalle="'Nombre Materia' está vacío"))
            continue
        if not nombre_area:
            errores.append(ImportacionMallaErrorItem(fila=fila_num, detalle="'Area' está vacío"))
            continue
        if not nombre_semestre:
            errores.append(ImportacionMallaErrorItem(fila=fila_num, detalle="'Semestre' está vacío"))
            continue

        area = areas_cache.get(nombre_area)
        if not area:
            errores.append(
                ImportacionMallaErrorItem(
                    fila=fila_num,
                    detalle=f"El área '{nombre_area}' no existe en el sistema. Solo se pueden usar áreas previamente registradas.",
                )
            )
            continue

        semestre = semestres_cache.get(nombre_semestre)
        if not semestre:
            errores.append(
                ImportacionMallaErrorItem(
                    fila=fila_num,
                    detalle=f"El semestre '{nombre_semestre}' no existe en el sistema. Solo se pueden usar semestres previamente registrados.",
                )
            )
            continue

        materia = materias_cache[nombre_materia]

        clave = (materia.id, area.id, semestre.id, nombre_malla)
        if clave in malla_cache:
            ya_existentes += 1
            continue

        nuevo_registro = MallaCurricular(
            materia_id=materia.id,
            area_id=area.id,
            semestre_id=semestre.id,
            nombre_malla=nombre_malla,
        )
        db.add(nuevo_registro)
        await db.flush()
        malla_cache[clave] = nuevo_registro
        registros_creados += 1

    return ImportacionMallaResponse(
        nombre_archivo=nombre_archivo,
        filas_procesadas=len(df),
        registros_creados=registros_creados,
        materias_creadas=materias_creadas,
        ya_existentes=ya_existentes,
        errores=errores,
    )
