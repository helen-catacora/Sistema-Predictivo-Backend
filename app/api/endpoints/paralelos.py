"""Endpoints de paralelos."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Paralelo
from app.schemas.paralelo import ParaleloItem, ParaleloListResponse

router = APIRouter(prefix="/paralelos", tags=["paralelos"])


@router.get(
    "",
    response_model=ParaleloListResponse,
    summary="Listar paralelos",
    description="Lista todos los paralelos con id, nombre y nombre del encargado.",
)
async def listar_paralelos(db: AsyncSession = Depends(get_db)):
    """Devuelve los paralelos con id, nombre del paralelo y nombre del encargado."""
    q = (
        select(Paralelo)
        .options(selectinload(Paralelo.encargado))
        .order_by(Paralelo.nombre)
    )
    result = await db.execute(q)
    paralelos = result.scalars().unique().all()

    items = [
        ParaleloItem(
            id=p.id,
            nombre=p.nombre,
            nombre_encargado=p.encargado.nombre if p.encargado else "",
        )
        for p in paralelos
    ]
    return ParaleloListResponse(paralelos=items)
