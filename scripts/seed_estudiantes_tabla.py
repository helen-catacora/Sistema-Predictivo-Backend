"""Seed: estudiantes y asistencias para probar GET /api/v1/estudiantes/tabla."""
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Area, Asistencia, Estudiante, Materia, Paralelo, Rol, Usuario
from app.models.asistencia import EstadoAsistencia

# Estudiantes de prueba (nombre, apellido, código)
ESTUDIANTES = [
    ("Alejandro", "Morales", "EMI-2024-0012"),
    ("Luciana", "Beltrán", "EMI-2024-0085"),
    ("Sofía", "Gutiérrez", "EMI-2024-0044"),
    ("Carlos", "Rodríguez", "EMI-2024-0104"),
    ("Valentina", "Ruiz", "EMI-2024-0099"),
    ("Mateo", "Fernández", "EMI-2024-0023"),
]

# Por cada estudiante: proporción (presente, ausente, justificado) en 10 registros → % distinto
# (p, a, j) -> % = (p+j)/10*100
ASISTENCIA_POR_ESTUDIANTE = [
    (6, 2, 2),   # 80%
    (8, 1, 1),   # 90%
    (4, 4, 2),   # 60%
    (9, 1, 0),   # 90%
    (4, 5, 1),   # 50%
    (7, 2, 1),   # 80%
]


async def seed():
    async with AsyncSessionLocal() as session:
        # 1. Área (usar id=1 o crear)
        r = await session.execute(select(Area).limit(1))
        area = r.scalar_one_or_none()
        if not area:
            area = Area(nombre="Tecnologicas")
            session.add(area)
            await session.flush()
            print("  + Área creada: Tecnologicas")
        else:
            print(f"  = Área existente: {area.nombre} (id={area.id})")

        # 2. Usuario encargado (el de prueba o el primero)
        r = await session.execute(select(Usuario).limit(1))
        encargado = r.scalar_one_or_none()
        if not encargado:
            r = await session.execute(select(Rol).limit(1))
            rol = r.scalar_one_or_none()
            if not rol:
                rol = Rol(nombre="Encargado")
                session.add(rol)
                await session.flush()
            encargado = Usuario(nombre="Encargado Prueba", email="encargado@test.edu", rol_id=rol.id)
            session.add(encargado)
            await session.flush()
            print("  + Usuario encargado creado")
        else:
            print(f"  = Encargado: {encargado.email} (id={encargado.id})")

        # 3. Paralelo
        r = await session.execute(
            select(Paralelo).where(Paralelo.area_id == area.id, Paralelo.nombre == "1-A")
        )
        paralelo = r.scalar_one_or_none()
        if not paralelo:
            paralelo = Paralelo(nombre="1-A", area_id=area.id, encargado_id=encargado.id)
            session.add(paralelo)
            await session.flush()
            print("  + Paralelo creado: 1-A")
        else:
            print(f"  = Paralelo existente: 1-A (id={paralelo.id})")

        # 4. Materia (para asistencias)
        r = await session.execute(select(Materia).limit(1))
        materia = r.scalar_one_or_none()
        if not materia:
            print("  ! Ejecuta antes: python scripts/seed_materias.py")
            await session.rollback()
            return
        print(f"  = Materia: {materia.nombre} (id={materia.id})")

        # 5. Estudiantes
        base_date = date.today() - timedelta(days=30)
        estudiantes_creados = []
        for i, (nombre, apellido, codigo) in enumerate(ESTUDIANTES):
            r = await session.execute(select(Estudiante).where(Estudiante.codigo_estudiante == codigo))
            if r.scalar_one_or_none():
                continue
            e = Estudiante(
                nombre=nombre,
                apellido=apellido,
                codigo_estudiante=codigo,
                paralelo_id=paralelo.id,
            )
            session.add(e)
            await session.flush()
            estudiantes_creados.append((e, ASISTENCIA_POR_ESTUDIANTE[i % len(ASISTENCIA_POR_ESTUDIANTE)]))
            print(f"  + Estudiante: {nombre} {apellido} ({codigo})")

        # 6. Asistencias (10 fechas por estudiante, mix Presente/Ausente/Justificado)
        for est, (np, na, nj) in estudiantes_creados:
            estados = (
                [EstadoAsistencia.PRESENTE] * np
                + [EstadoAsistencia.AUSENTE] * na
                + [EstadoAsistencia.JUSTIFICADO] * nj
            )
            for d in range(10):
                fecha = base_date + timedelta(days=d)
                estado = estados[d] if d < len(estados) else EstadoAsistencia.PRESENTE
                a = Asistencia(
                    fecha=fecha,
                    estado=estado,
                    estudiante_id=est.id,
                    materia_id=materia.id,
                    encargado_id=encargado.id,
                )
                session.add(a)
            print(f"    -> 10 asistencias para {est.nombre} ({np}P, {na}A, {nj}J)")

        await session.commit()
    print("Listo. Prueba: GET /api/v1/estudiantes/tabla o ?paralelo_id=1")


if __name__ == "__main__":
    asyncio.run(seed())
