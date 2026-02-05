"""Endpoints de materias (desde malla_curricular)."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import MallaCurricular
from app.schemas.materia import MateriaItem, MateriaListResponse

router = APIRouter(prefix="/materias", tags=["materias"])


@router.get(
    "",
    response_model=MateriaListResponse,
    summary="Listar materias (malla curricular)",
    description="Lista las materias desde la malla curricular (materia_id, area_id, semestre_id). Opcional: filtrar por area_id y/o semestre_id.",
)
async def listar_materias(
    db: AsyncSession = Depends(get_db),
    area_id: Annotated[int | None, Query(description="Filtrar por ID del área")] = None,
    semestre_id: Annotated[int | None, Query(description="Filtrar por ID del semestre")] = None,
):
    """Devuelve las materias que están en la malla curricular, con area_id y semestre_id. Opcionalmente filtradas por área y/o semestre."""
    q = (
        select(MallaCurricular)
        .options(selectinload(MallaCurricular.materia))
        .where(MallaCurricular.materia_id.isnot(None))
        .order_by(MallaCurricular.area_id, MallaCurricular.semestre_id, MallaCurricular.materia_id)
    )
    if area_id is not None:
        q = q.where(MallaCurricular.area_id == area_id)
    if semestre_id is not None:
        q = q.where(MallaCurricular.semestre_id == semestre_id)

    result = await db.execute(q)
    filas = result.scalars().unique().all()

    items = []
    for row in filas:
        if row.materia:
            items.append(
                MateriaItem(
                    id=row.materia.id,
                    nombre=row.materia.nombre,
                    area_id=row.area_id,
                    semestre_id=row.semestre_id,
                )
            )
    return MateriaListResponse(materias=items)
