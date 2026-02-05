"""Endpoints de paralelos. Requiere JWT; Superadministrador/Administrador ven todos, el resto solo los que tienen como encargado."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models import Paralelo, Rol, Usuario
from app.schemas.paralelo import ParaleloItem, ParaleloListResponse

# Roles que ven todos los paralelos (nombre normalizado: minúsculas y sin espacios)
ROLES_VEN_TODOS_PARALELOS = ("superadministrador", "administrador")


def _nombre_rol_normalizado(nombre: str | None) -> str:
    """Minúsculas y sin espacios, para comparar con independencia de formato en BD."""
    if not nombre:
        return ""
    return (nombre or "").strip().lower().replace(" ", "")

router = APIRouter(prefix="/paralelos", tags=["paralelos"])


@router.get(
    "",
    response_model=ParaleloListResponse,
    summary="Listar paralelos",
    description="Requiere JWT. Superadministrador/Administrador: todos los paralelos. Otros: solo los que tienen como encargado. Incluye area_id y semestre_id.",
)
async def listar_paralelos(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Devuelve paralelos según el rol: todos si es Superadministrador/Administrador, si no solo los del encargado."""
    q = (
        select(Paralelo)
        .options(selectinload(Paralelo.encargado))
        .order_by(Paralelo.nombre)
    )
    # Consultar nombre del rol directamente (evita problemas de sesión/identity map)
    r_rol = await db.execute(
        select(Rol.nombre).join(Usuario, Usuario.rol_id == Rol.id).where(Usuario.id == current_user.id)
    )
    nombre_rol = r_rol.scalar_one_or_none()
    rol_ok = _nombre_rol_normalizado(nombre_rol) in ROLES_VEN_TODOS_PARALELOS
    if not rol_ok:
        q = q.where(Paralelo.encargado_id == current_user.id)

    result = await db.execute(q)
    paralelos = result.scalars().unique().all()

    items = [
        ParaleloItem(
            id=p.id,
            nombre=p.nombre,
            area_id=p.area_id,
            semestre_id=p.semestre_id,
            nombre_encargado=p.encargado.nombre if p.encargado else "",
        )
        for p in paralelos
    ]
    return ParaleloListResponse(paralelos=items)
