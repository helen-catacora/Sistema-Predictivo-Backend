"""Script para insertar registros en malla_curricular (materia + área + semestre)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Materia, MallaCurricular

# Bloques: (area_id, semestre_id, lista de nombres de materias)
BLOQUES_MALLA = [
    (1, 1, [
        "Algebra (T)", "Calculo I (T)", "Fisica I (T)", "Fisica I (L)",
        "Quimica Aplicada (T)", "Quimica Aplicada (L)", "Programación I",
    ]),
    (2, 1, [
        "Algebra (T)", "Calculo I (T)", "Fisica I (T)", "Fisica I (L)",
        "Quimica Aplicada (T)", "Quimica Aplicada (L)", "Dibujo para la Ingeniería",
    ]),
    (1, 2, [
        "Algebra Lineal (T)", "Calculo II (T)", "Fisica II (T)", "Fisica II (L)",
        "Estadistica", "Programación II", "Componentes, Instrumentacion Electronica",
    ]),
    (2, 2, [
        "Algebra Lineal (T)", "Calculo II (T)", "Fisica II (T)", "Fisica II (L)",
        "Estadistica", "Programación",
    ]),
]


async def seed_malla(bloques=None):
    bloques = bloques or BLOQUES_MALLA
    async with AsyncSessionLocal() as session:
        for area_id, semestre_id, materias in bloques:
            for nombre in materias:
                nombre = nombre.strip()
                if not nombre:
                    continue
                result = await session.execute(select(Materia).where(Materia.nombre == nombre))
                materia = result.scalar_one_or_none()
                if not materia:
                    print(f"  ! Materia no encontrada: {nombre}")
                    continue
                exists = await session.execute(
                    select(MallaCurricular).where(
                        MallaCurricular.materia_id == materia.id,
                        MallaCurricular.area_id == area_id,
                        MallaCurricular.semestre_id == semestre_id,
                    )
                )
                if exists.scalar_one_or_none():
                    print(f"  = {nombre} (ya en malla area={area_id} semestre={semestre_id})")
                else:
                    session.add(
                        MallaCurricular(
                            materia_id=materia.id,
                            area_id=area_id,
                            semestre_id=semestre_id,
                        )
                    )
                    print(f"  + {nombre} -> area_id={area_id}, semestre_id={semestre_id}")
        await session.commit()
    print("Listo.")


if __name__ == "__main__":
    asyncio.run(seed_malla())
