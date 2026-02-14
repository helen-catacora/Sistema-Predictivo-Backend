"""Servicio de alertas para riesgo de abandono estudiantil."""
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerta import Alerta, TipoAlerta, EstadoAlerta
from app.models.asistencia import Asistencia, EstadoAsistencia
from app.models.prediccion import Prediccion, NivelRiesgo


async def resolver_alertas_por_mejora(
    estudiante_id: int,
    nivel_riesgo_nuevo: str,
    probabilidad_nueva: float,
    db: AsyncSession,
) -> int:
    """Resuelve automáticamente alertas activas cuando el riesgo baja a Bajo o Medio."""
    q = (
        select(Alerta)
        .where(
            Alerta.estudiante_id == estudiante_id,
            Alerta.estado.in_([EstadoAlerta.ACTIVA, EstadoAlerta.EN_SEGUIMIENTO]),
        )
    )
    result = await db.execute(q)
    alertas_abiertas = result.scalars().all()

    ahora = datetime.now(timezone.utc)
    resueltas = 0
    for alerta in alertas_abiertas:
        alerta.estado = EstadoAlerta.RESUELTA
        alerta.fecha_resolucion = ahora
        alerta.observacion_resolucion = (
            f"Resuelta automáticamente: el riesgo pasó de {alerta.nivel} "
            f"a {nivel_riesgo_nuevo} ({probabilidad_nueva:.1%}) "
            f"según predicción del {ahora.strftime('%d/%m/%Y')}."
        )
        resueltas += 1

    return resueltas


async def generar_alertas_prediccion(
    estudiante_id: int,
    prediccion_id: int,
    nivel_riesgo: str,
    probabilidad: float,
    db: AsyncSession,
    gestion_id: int | None = None,
) -> Alerta | None:
    """Crea alerta si riesgo Alto/Critico; resuelve alertas anteriores si el riesgo bajó."""
    if nivel_riesgo not in (NivelRiesgo.ALTO, NivelRiesgo.CRITICO):
        await resolver_alertas_por_mejora(
            estudiante_id, nivel_riesgo, probabilidad, db,
        )
        return None

    alerta = Alerta(
        tipo=TipoAlerta.TEMPRANA,
        nivel=nivel_riesgo,
        estudiante_id=estudiante_id,
        prediccion_id=prediccion_id,
        titulo=f"Riesgo {nivel_riesgo} de abandono ({probabilidad:.0%})",
        descripcion=(
            f"El modelo predictivo indica una probabilidad de abandono del "
            f"{probabilidad:.1%} (nivel {nivel_riesgo})."
        ),
        estado=EstadoAlerta.ACTIVA,
        gestion_id=gestion_id,
    )
    db.add(alerta)
    return alerta


async def verificar_inasistencias_consecutivas(
    estudiante_id: int,
    materia_id: int,
    db: AsyncSession,
) -> int:
    """Cuenta las faltas consecutivas más recientes del estudiante en una materia."""
    q = (
        select(Asistencia.estado)
        .where(
            Asistencia.estudiante_id == estudiante_id,
            Asistencia.materia_id == materia_id,
        )
        .order_by(Asistencia.fecha.desc())
    )
    result = await db.execute(q)
    registros = result.scalars().all()

    faltas = 0
    for estado in registros:
        if estado == EstadoAsistencia.AUSENTE:
            faltas += 1
        else:
            break
    return faltas


async def evaluar_alertas_asistencia(
    estudiante_id: int,
    materia_id: int,
    db: AsyncSession,
    gestion_id: int | None = None,
) -> Alerta | None:
    """Evalúa si se debe generar una alerta crítica o de abandono tras registrar asistencia."""
    faltas = await verificar_inasistencias_consecutivas(estudiante_id, materia_id, db)

    if faltas <= 2:
        return None

    # Obtener la predicción más reciente del estudiante
    q_pred = (
        select(Prediccion)
        .where(Prediccion.estudiante_id == estudiante_id)
        .order_by(Prediccion.fecha_prediccion.desc())
        .limit(1)
    )
    result = await db.execute(q_pred)
    ultima_prediccion = result.scalar_one_or_none()

    nivel_riesgo = ultima_prediccion.nivel_riesgo if ultima_prediccion else None

    # 5+ faltas consecutivas = alerta de abandono (criterio institucional)
    if faltas >= 5:
        alerta = Alerta(
            tipo=TipoAlerta.ABANDONO,
            nivel=NivelRiesgo.CRITICO,
            estudiante_id=estudiante_id,
            prediccion_id=ultima_prediccion.id if ultima_prediccion else None,
            titulo=f"Posible abandono: {faltas} inasistencias consecutivas",
            descripcion=(
                f"El estudiante acumula {faltas} faltas consecutivas, "
                f"superando el criterio institucional de 5 faltas."
            ),
            estado=EstadoAlerta.ACTIVA,
            faltas_consecutivas=faltas,
            gestion_id=gestion_id,
        )
        db.add(alerta)
        return alerta

    # 3+ faltas con riesgo Alto/Critico = alerta crítica
    if faltas >= 3 and nivel_riesgo in (NivelRiesgo.ALTO, NivelRiesgo.CRITICO):
        alerta = Alerta(
            tipo=TipoAlerta.CRITICA,
            nivel=nivel_riesgo,
            estudiante_id=estudiante_id,
            prediccion_id=ultima_prediccion.id if ultima_prediccion else None,
            titulo=f"Riesgo {nivel_riesgo} + {faltas} inasistencias consecutivas",
            descripcion=(
                f"El estudiante tiene riesgo {nivel_riesgo} de abandono y "
                f"acumula {faltas} faltas consecutivas."
            ),
            estado=EstadoAlerta.ACTIVA,
            faltas_consecutivas=faltas,
            gestion_id=gestion_id,
        )
        db.add(alerta)
        return alerta

    return None
