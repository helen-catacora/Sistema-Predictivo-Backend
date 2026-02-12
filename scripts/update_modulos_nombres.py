"""Actualiza los nombres de los módulos en la BD a los nombres descriptivos del sistema."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Modulo

RENOMBRAR = {
    "configuracion": "Gestión de Usuarios",
    "estudiantes": "Gestión de Datos de Estudiantes",
    "predicciones": "Visualización de Resultados",
    "asistencias": "Control de Asistencia",
    "reportes": "Reportes",
}


async def update_nombres():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Modulo))
        modulos = result.scalars().all()

        print("Estado actual:")
        for m in modulos:
            print(f"  id={m.id} | nombre={m.nombre}")

        print("\nActualizando nombres...")
        for m in modulos:
            if m.nombre in RENOMBRAR:
                nuevo = RENOMBRAR[m.nombre]
                print(f"  {m.nombre} -> {nuevo}")
                m.nombre = nuevo

        await session.commit()

        # Verificar
        result = await session.execute(select(Modulo).order_by(Modulo.id))
        modulos = result.scalars().all()
        print("\nEstado final:")
        for m in modulos:
            print(f"  id={m.id} | nombre={m.nombre}")


if __name__ == "__main__":
    asyncio.run(update_nombres())
