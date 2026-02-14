"""Genera alertas retroactivas de asistencia para estudiantes con inasistencias consecutivas.

Recorre todos los estudiantes, evalúa sus inasistencias por materia
y genera alertas (critica o abandono) según corresponda.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models import Asistencia, Estudiante, Materia
from app.services.alerta_service import (
    evaluar_alertas_asistencia,
    verificar_inasistencias_consecutivas,
)


async def main():
    async with AsyncSessionLocal() as db:
        # Diagnóstico del estudiante 27
        print("=" * 60)
        print("DIAGNÓSTICO ESTUDIANTE 27")
        print("=" * 60)

        # Materias con asistencia del estudiante 27
        q_materias = (
            select(Asistencia.materia_id, Materia.nombre)
            .join(Materia, Materia.id == Asistencia.materia_id)
            .where(Asistencia.estudiante_id == 27)
            .distinct()
        )
        result = await db.execute(q_materias)
        materias_est27 = result.all()

        for materia_id, materia_nombre in materias_est27:
            # Ver los registros ordenados por fecha DESC
            q_detalle = (
                select(Asistencia.fecha, Asistencia.estado)
                .where(
                    Asistencia.estudiante_id == 27,
                    Asistencia.materia_id == materia_id,
                )
                .order_by(Asistencia.fecha.desc())
            )
            result = await db.execute(q_detalle)
            registros = result.all()

            faltas = await verificar_inasistencias_consecutivas(27, materia_id, db)

            print(f"\nMateria: {materia_nombre} (id={materia_id})")
            print(f"  Faltas consecutivas (desde más reciente): {faltas}")
            print(f"  Registros (más reciente primero):")
            for fecha, estado in registros[:10]:
                print(f"    {fecha} -> {estado}")

        # Ahora generar alertas para TODOS
        print("\n" + "=" * 60)
        print("GENERANDO ALERTAS PARA TODOS LOS ESTUDIANTES")
        print("=" * 60)

        q = (
            select(
                Asistencia.estudiante_id,
                Asistencia.materia_id,
            )
            .distinct()
        )
        result = await db.execute(q)
        pares = result.all()

        print(f"Evaluando {len(pares)} combinaciones estudiante-materia...")

        alertas_generadas = 0
        for estudiante_id, materia_id in pares:
            alerta = await evaluar_alertas_asistencia(estudiante_id, materia_id, db)
            if alerta:
                alertas_generadas += 1
                print(
                    f"  Alerta generada: estudiante={estudiante_id}, "
                    f"materia={materia_id}, tipo={alerta.tipo}, "
                    f"faltas={alerta.faltas_consecutivas}"
                )

        await db.commit()
        print(f"\nTotal alertas generadas: {alertas_generadas}")


if __name__ == "__main__":
    asyncio.run(main())
