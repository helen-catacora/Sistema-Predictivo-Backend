"""Endpoints de materias."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Materia
from app.schemas.materia import MateriaItem, MateriaListResponse

router = APIRouter(prefix="/materias", tags=["materias"])


@router.get(
    "",
    response_model=MateriaListResponse,
    summary="Listar materias",
    description="Lista todas las materias con id y nombre.",
)
async def listar_materias(db: AsyncSession = Depends(get_db)):
    """Devuelve todas las materias ordenadas por nombre."""
    result = await db.execute(select(Materia).order_by(Materia.nombre))
    materias = result.scalars().all()
    items = [MateriaItem(id=m.id, nombre=m.nombre) for m in materias]
    return MateriaListResponse(materias=items)
