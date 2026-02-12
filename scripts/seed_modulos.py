"""Actualiza la tabla modulos con los 5 módulos actuales del sistema."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Modulo

# Módulos actuales del sistema
MODULOS = [
    "Gestión de Usuarios",
    "Gestión de Datos de Estudiantes",
    "Visualización de Resultados",
    "Control de Asistencia",
    "Reportes",
]


async def seed_modulos():
    async with AsyncSessionLocal() as session:
        # Obtener módulos existentes
        result = await session.execute(select(Modulo))
        existentes = {m.nombre: m for m in result.scalars().all()}

        print("Módulos existentes en la BD:", list(existentes.keys()) if existentes else "(ninguno)")

        # Crear módulos faltantes
        creados = []
        for nombre in MODULOS:
            if nombre not in existentes:
                modulo = Modulo(nombre=nombre)
                session.add(modulo)
                creados.append(nombre)

        if creados:
            await session.commit()
            print(f"Módulos creados: {creados}")
        else:
            print("Todos los módulos ya existen, no se crearon nuevos.")

        # Mostrar estado final
        result = await session.execute(select(Modulo).order_by(Modulo.id))
        todos = result.scalars().all()
        print("\nMódulos actuales en la BD:")
        for m in todos:
            print(f"  id={m.id} | nombre={m.nombre}")


if __name__ == "__main__":
    asyncio.run(seed_modulos())
