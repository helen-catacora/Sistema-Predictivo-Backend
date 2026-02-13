"""Seed: 50 estudiantes ficticios + inscripciones, asistencias, predicciones, alertas y acciones.

NO toca: roles, semestres, materias, areas, malla_curricular (deben existir previamente).
"""
import asyncio
import random
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import (
    Accion,
    Alerta,
    Area,
    Asistencia,
    Estudiante,
    GestionAcademica,
    Inscripcion,
    LotePrediccion,
    Materia,
    Paralelo,
    Prediccion,
    Semestre,
    Usuario,
)

random.seed(42)

# ── Datos ficticios ──────────────────────────────────────────────────

NOMBRES = [
    "Carlos", "María", "Juan", "Ana", "Pedro", "Lucía", "Diego", "Sofía",
    "Miguel", "Valentina", "Andrés", "Camila", "José", "Isabella", "Luis",
    "Daniela", "Fernando", "Gabriela", "Ricardo", "Natalia", "Alejandro",
    "Paula", "Sebastián", "Carolina", "Javier", "Mariana", "David", "Laura",
    "Tomás", "Andrea", "Nicolás", "Fernanda", "Mateo", "Claudia", "Santiago",
    "Verónica", "Emilio", "Diana", "Martín", "Pamela", "Gabriel", "Jimena",
    "Rafael", "Lorena", "Ignacio", "Mónica", "Adrián", "Silvana", "Rodrigo",
    "Elena",
]

APELLIDOS = [
    "García", "Rodríguez", "Martínez", "López", "Hernández", "González",
    "Pérez", "Sánchez", "Ramírez", "Torres", "Flores", "Rivera", "Gómez",
    "Díaz", "Cruz", "Morales", "Ortiz", "Gutiérrez", "Chávez", "Ramos",
    "Vargas", "Castillo", "Jiménez", "Moreno", "Romero", "Alvarado", "Ruiz",
    "Mendoza", "Aguilar", "Medina", "Castro", "Herrera", "Suárez", "Vega",
    "Salazar", "Delgado", "Rojas", "Ponce", "Espinoza", "Córdova", "Quispe",
    "Mamani", "Condori", "Huanca", "Choque", "Arancibia", "Vásquez",
    "Colque", "Limachi", "Ticona",
]

GENEROS = ["Masculino", "Femenino"]
GRADOS = ["Civil", "Militar"]
ESTRATOS = ["Alto", "Medio", "Bajo"]
OCUPACIONES = ["Si", "No"]
CON_QUIEN_VIVE = ["Con Familiares", "Con mi novia", "Con mis padres", "En residencia o alojamiento estudiantil", "Solo/a"]
APOYO_ECONOMICO = ["Ninguno", "Parcial", "Total"]
MODALIDADES = ["Admision Especial", "Curso Preuniversitario/Intensivo", "Curso Vestibular", "Prueba de Suficiencia Academica"]
TIPOS_COLEGIO = ["Convenio", "Privado", "Publico"]

ESTADOS_ASISTENCIA = ["Presente", "Presente", "Presente", "Ausente", "Justificado"]


def fecha_nacimiento_random() -> date:
    """Genera fecha de nacimiento para estudiantes de 17-28 años."""
    edad = random.randint(17, 28)
    return date(date.today().year - edad, random.randint(1, 12), random.randint(1, 28))


def calcular_nivel(prob: float) -> str:
    if prob >= 0.7:
        return "Critico"
    elif prob >= 0.5:
        return "Alto"
    elif prob >= 0.3:
        return "Medio"
    return "Bajo"


async def seed():
    async with AsyncSessionLocal() as session:
        # ── 1. Verificar datos existentes ────────────────────────────
        areas = (await session.execute(select(Area).order_by(Area.id))).scalars().all()
        semestres = (await session.execute(select(Semestre).order_by(Semestre.id))).scalars().all()
        materias = (await session.execute(select(Materia).order_by(Materia.id))).scalars().all()
        usuarios = (await session.execute(select(Usuario).order_by(Usuario.id))).scalars().all()

        if not areas:
            print("ERROR: No hay áreas en la BD. Crea áreas primero.")
            return
        if not semestres:
            print("ERROR: No hay semestres en la BD. Crea semestres primero.")
            return
        if not materias:
            print("ERROR: No hay materias en la BD. Crea materias primero.")
            return
        if not usuarios:
            print("ERROR: No hay usuarios en la BD. Crea usuarios primero.")
            return

        print(f"  Areas: {[a.nombre for a in areas]}")
        print(f"  Semestres: {[s.nombre for s in semestres]}")
        print(f"  Materias: {[m.nombre for m in materias]}")
        print(f"  Usuarios: {[u.nombre for u in usuarios]}")

        encargado = usuarios[0]

        # ── 2. Gestión académica ─────────────────────────────────────
        r = await session.execute(select(GestionAcademica).where(GestionAcademica.activa == True))
        gestion = r.scalar_one_or_none()
        if not gestion:
            gestion = GestionAcademica(
                nombre="I-2026",
                fecha_inicio=date(2026, 2, 1),
                fecha_fin=date(2026, 7, 15),
                activa=True,
            )
            session.add(gestion)
            await session.flush()
            print(f"  + Gestión creada: {gestion.nombre} (id={gestion.id})")
        else:
            print(f"  = Gestión activa existente: {gestion.nombre} (id={gestion.id})")

        # ── 3. Paralelos ─────────────────────────────────────────────
        r_par = await session.execute(select(Paralelo))
        paralelos_existentes = r_par.scalars().all()

        if paralelos_existentes:
            paralelos = paralelos_existentes
            print(f"  = Paralelos existentes: {len(paralelos)}")
        else:
            paralelos = []
            nombres_paralelo = ["A", "B"]
            for area in areas:
                sem = semestres[0] if semestres else None
                for letra in nombres_paralelo:
                    nombre_par = f"{area.nombre[:15]}-{letra}"
                    p = Paralelo(
                        nombre=nombre_par,
                        area_id=area.id,
                        semestre_id=sem.id if sem else None,
                        encargado_id=encargado.id,
                    )
                    session.add(p)
                    paralelos.append(p)
            await session.flush()
            print(f"  + Paralelos creados: {len(paralelos)}")

        for p in paralelos:
            print(f"    id={p.id} | {p.nombre}")

        # ── 4. Estudiantes (50) ──────────────────────────────────────
        r_est = await session.execute(select(Estudiante))
        existentes = r_est.scalars().all()
        codigos_existentes = {e.codigo_estudiante for e in existentes}

        estudiantes_nuevos = []
        for i in range(50):
            codigo = f"EST-2026-{i+1:03d}"
            if codigo in codigos_existentes:
                continue

            paralelo = random.choice(paralelos)
            est = Estudiante(
                codigo_estudiante=codigo,
                nombre=NOMBRES[i],
                apellido=random.choice(APELLIDOS),
                paralelo_id=paralelo.id,
                fecha_nacimiento=fecha_nacimiento_random(),
                genero=random.choice(GENEROS),
                grado=random.choice(GRADOS),
                estrato_socioeconomico=random.choice(ESTRATOS),
                ocupacion_laboral=random.choice(OCUPACIONES),
                con_quien_vive=random.choice(CON_QUIEN_VIVE),
                apoyo_economico=random.choice(APOYO_ECONOMICO),
                modalidad_ingreso=random.choice(MODALIDADES),
                tipo_colegio=random.choice(TIPOS_COLEGIO),
            )
            session.add(est)
            estudiantes_nuevos.append(est)

        await session.flush()
        print(f"  + Estudiantes creados: {len(estudiantes_nuevos)}")

        # Todos los estudiantes (existentes + nuevos)
        r_todos = await session.execute(select(Estudiante).order_by(Estudiante.id))
        todos_estudiantes = r_todos.scalars().all()
        print(f"  Total estudiantes en BD: {len(todos_estudiantes)}")

        # ── 5. Inscripciones ─────────────────────────────────────────
        # Solo crear para estudiantes que no tengan inscripciones
        r_ids_con_insc = await session.execute(
            select(Inscripcion.estudiante_id).distinct()
        )
        ids_con_insc = {row[0] for row in r_ids_con_insc.all()}
        est_sin_insc = [e for e in todos_estudiantes if e.id not in ids_con_insc]

        if not est_sin_insc:
            print("  = Todos los estudiantes ya tienen inscripciones, saltando...")
        else:
            count_insc = 0
            for est in est_sin_insc:
                # Cada estudiante se inscribe en 3-5 materias aleatorias
                n_materias = min(random.randint(3, 5), len(materias))
                mats_seleccionadas = random.sample(materias, n_materias)
                for mat in mats_seleccionadas:
                    insc = Inscripcion(
                        estudiante_id=est.id,
                        materia_id=mat.id,
                        gestion_academica=gestion.nombre,
                        gestion_id=gestion.id,
                    )
                    session.add(insc)
                    count_insc += 1
            await session.flush()
            print(f"  + Inscripciones creadas: {count_insc}")

        # ── 6. Asistencias (últimas 4 semanas) ──────────────────────
        r_ids_con_asis = await session.execute(
            select(Asistencia.estudiante_id).distinct()
        )
        ids_con_asis = {row[0] for row in r_ids_con_asis.all()}
        est_sin_asis = [e for e in todos_estudiantes if e.id not in ids_con_asis]

        if not est_sin_asis:
            print("  = Todos los estudiantes ya tienen asistencias, saltando...")
        else:
            # Generar fechas de clase (lunes a viernes, últimas 4 semanas)
            hoy = date.today()
            fechas_clase = []
            for delta in range(28):
                d = hoy - timedelta(days=delta)
                if d.weekday() < 5:  # lun-vie
                    fechas_clase.append(d)
            fechas_clase.sort()

            count_asis = 0
            for est in est_sin_asis:
                # Obtener materias inscritas
                r_mi = await session.execute(
                    select(Inscripcion.materia_id).where(
                        Inscripcion.estudiante_id == est.id
                    )
                )
                materia_ids = [row[0] for row in r_mi.all()]
                if not materia_ids:
                    continue

                # 1-2 clases por semana por materia
                for mat_id in materia_ids:
                    dias_clase = random.sample(
                        fechas_clase, min(random.randint(6, 10), len(fechas_clase))
                    )
                    for fecha in dias_clase:
                        estado = random.choice(ESTADOS_ASISTENCIA)
                        asis = Asistencia(
                            fecha=fecha,
                            estado=estado,
                            estudiante_id=est.id,
                            materia_id=mat_id,
                            encargado_id=encargado.id,
                        )
                        session.add(asis)
                        count_asis += 1

            await session.flush()
            print(f"  + Asistencias creadas: {count_asis}")

        # ── 7. Lote de predicción ────────────────────────────────────
        lote = LotePrediccion(
            nombre_archivo="seed_prediccion_masiva.xlsx",
            usuario_id=encargado.id,
            gestion_id=gestion.id,
            estado="completado",
            total_estudiantes=len(todos_estudiantes),
            total_procesados=len(todos_estudiantes),
            version_modelo="v2_con_imputacion_knn",
        )
        session.add(lote)
        await session.flush()
        print(f"  + Lote creado: id={lote.id}")

        # ── 8. Predicciones ──────────────────────────────────────────
        contadores = {"Bajo": 0, "Medio": 0, "Alto": 0, "Critico": 0}
        predicciones_map: dict[int, Prediccion] = {}

        for est in todos_estudiantes:
            # Distribución realista: ~40% Bajo, ~25% Medio, ~20% Alto, ~15% Critico
            r_val = random.random()
            if r_val < 0.40:
                prob = round(random.uniform(0.05, 0.29), 4)
            elif r_val < 0.65:
                prob = round(random.uniform(0.30, 0.49), 4)
            elif r_val < 0.85:
                prob = round(random.uniform(0.50, 0.69), 4)
            else:
                prob = round(random.uniform(0.70, 0.95), 4)

            nivel = calcular_nivel(prob)
            contadores[nivel] += 1

            # Features simuladas
            features = {
                "Mat": random.randint(3, 8),
                "Rep": random.randint(0, 4),
                "2T": random.randint(0, 3),
                "Prom": round(random.uniform(35, 90), 1),
                "edad": random.randint(17, 28),
                "Grado": est.grado,
                "Genero": est.genero,
                "Semestre": "Primer" if random.random() < 0.5 else "Segundo",
                "Carrera": "Tecnologicas" if random.random() < 0.5 else "No Tecnologicas",
                "estrato_socioeconomico": est.estrato_socioeconomico,
                "ocupacion_laboral": est.ocupacion_laboral,
                "con_quien_vive": est.con_quien_vive,
                "apoyo_economico": est.apoyo_economico,
                "modalidad_ingreso": est.modalidad_ingreso,
                "tipo_colegio": est.tipo_colegio,
            }

            pred = Prediccion(
                probabilidad_abandono=prob,
                nivel_riesgo=nivel,
                fecha_prediccion=date.today() - timedelta(days=random.randint(0, 14)),
                estudiante_id=est.id,
                lote_id=lote.id,
                gestion_id=gestion.id,
                tipo="masiva",
                features_utilizadas=features,
                version_modelo="v2_con_imputacion_knn",
            )
            session.add(pred)
            predicciones_map[est.id] = pred

        await session.flush()

        # Actualizar contadores del lote
        lote.total_bajo_riesgo = contadores["Bajo"]
        lote.total_medio_riesgo = contadores["Medio"]
        lote.total_alto_riesgo = contadores["Alto"]
        lote.total_critico = contadores["Critico"]

        print(f"  + Predicciones creadas: {sum(contadores.values())}")
        print(f"    Bajo: {contadores['Bajo']} | Medio: {contadores['Medio']} "
              f"| Alto: {contadores['Alto']} | Critico: {contadores['Critico']}")

        # ── 9. Alertas ───────────────────────────────────────────────
        count_alertas = 0
        for est_id, pred in predicciones_map.items():
            if pred.nivel_riesgo in ("Alto", "Critico"):
                # Alerta temprana por predicción
                alerta = Alerta(
                    tipo="temprana",
                    nivel=pred.nivel_riesgo,
                    estudiante_id=est_id,
                    prediccion_id=pred.id,
                    titulo=f"Riesgo {pred.nivel_riesgo} de abandono ({pred.probabilidad_abandono:.0%})",
                    descripcion=(
                        f"El modelo predictivo indica una probabilidad de abandono del "
                        f"{pred.probabilidad_abandono:.1%} (nivel {pred.nivel_riesgo})."
                    ),
                    estado="activa",
                    faltas_consecutivas=0,
                    gestion_id=gestion.id,
                )
                session.add(alerta)
                count_alertas += 1

                # Algunas alertas críticas por inasistencias (30% de los de alto riesgo)
                if random.random() < 0.30:
                    faltas = random.randint(3, 6)
                    tipo_alerta = "abandono" if faltas > 5 else "critica"
                    alerta_asis = Alerta(
                        tipo=tipo_alerta,
                        nivel=pred.nivel_riesgo,
                        estudiante_id=est_id,
                        prediccion_id=pred.id,
                        titulo=f"{'Posible abandono' if faltas > 5 else 'Riesgo ' + pred.nivel_riesgo}: {faltas} inasistencias consecutivas",
                        descripcion=(
                            f"El estudiante acumula {faltas} faltas consecutivas"
                            f"{', superando el criterio institucional de 5 faltas.' if faltas > 5 else '.'}"
                        ),
                        estado=random.choice(["activa", "activa", "en_seguimiento"]),
                        faltas_consecutivas=faltas,
                        gestion_id=gestion.id,
                    )
                    session.add(alerta_asis)
                    count_alertas += 1

        await session.flush()
        print(f"  + Alertas creadas: {count_alertas}")

        # ── 10. Acciones de seguimiento ──────────────────────────────
        count_acciones = 0
        acciones_desc = [
            "Entrevista con el estudiante para evaluar situación académica.",
            "Derivación a psicopedagogía para seguimiento.",
            "Reunión con tutor académico para plan de mejora.",
            "Llamada telefónica al estudiante para verificar estado.",
            "Contacto con familia del estudiante.",
            "Asignación de tutoría personalizada en materias críticas.",
            "Reunión de seguimiento con el estudiante y jefe de carrera.",
            "Aplicación de plan de recuperación académica.",
        ]

        for est_id, pred in predicciones_map.items():
            if pred.nivel_riesgo in ("Alto", "Critico") and random.random() < 0.40:
                n_acciones = random.randint(1, 3)
                for j in range(n_acciones):
                    accion = Accion(
                        descripcion=random.choice(acciones_desc),
                        fecha=date.today() - timedelta(days=random.randint(0, 20)),
                        prediccion_id=pred.id,
                    )
                    session.add(accion)
                    count_acciones += 1

        await session.flush()
        print(f"  + Acciones creadas: {count_acciones}")

        # ── Commit ───────────────────────────────────────────────────
        await session.commit()
        print("\n=== Seed completado exitosamente ===")


if __name__ == "__main__":
    asyncio.run(seed())
