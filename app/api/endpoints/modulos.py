"""Endpoints de módulos del sistema."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints.auth import require_module
from app.core.database import get_db
from app.models import Modulo, Usuario

router = APIRouter(prefix="/modulos", tags=["modulos"])


@router.get(
    "",
    summary="Listar módulos del sistema",
    description="Devuelve todos los módulos disponibles (id y nombre). Requiere módulo Gestión de Usuarios.",
)
async def listar_modulos(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Gestión de Usuarios")),
):
    """Devuelve la lista completa de módulos del sistema."""
    result = await db.execute(select(Modulo).order_by(Modulo.id))
    modulos = result.scalars().all()
    return {
        "modulos": [
            {"id": m.id, "nombre": m.nombre}
            for m in modulos
        ]
    }
