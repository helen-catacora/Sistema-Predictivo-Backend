"""Script para insertar las materias iniciales en la tabla materias."""
import asyncio
import sys
from pathlib import Path

# Asegurar que el proyecto esté en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Materia


MATERIAS = [
    "Algebra (T)",
    "Calculo I (T)",
    "Fisica I (T)",
    "Fisica I (L)",
    "Quimica Aplicada (T)",
    "Quimica Aplicada (L)",
    "Programación I",
    "Dibujo para la Ingeniería",
    "Algebra Lineal (T)",
    "Calculo II (T)",
    "Fisica II (T)",
    "Fisica II (L)",
    "Estadistica",
    "Programación",
    "Programación II",
    "Componentes, Instrumentacion Electronica",
]


async def seed_materias():
    async with AsyncSessionLocal() as session:
        for nombre in MATERIAS:
            nombre = nombre.strip()
            if not nombre:
                continue
            result = await session.execute(select(Materia).where(Materia.nombre == nombre))
            if result.scalar_one_or_none() is None:
                session.add(Materia(nombre=nombre))
                print(f"  + {nombre}")
            else:
                print(f"  = {nombre} (ya existe)")
        await session.commit()
    print("Listo.")


if __name__ == "__main__":
    asyncio.run(seed_materias())
