"""Endpoints de paralelos. Requiere JWT; Superadministrador/Administrador ven todos, el resto solo los que tienen como encargado."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import get_current_user, require_module
from app.core.database import get_db
from app.models import Area, Paralelo, Rol, Semestre, Usuario
from app.schemas.paralelo import ParaleloCreate, ParaleloItem, ParaleloListResponse, ParaleloUpdate

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
        .options(
            selectinload(Paralelo.encargado),
            selectinload(Paralelo.area),
        )
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
            area_nombre=p.area.nombre if p.area else None,
            semestre_id=p.semestre_id,
            encargado_id=p.encargado_id,
            nombre_encargado=p.encargado.nombre if p.encargado else "",
        )
        for p in paralelos
    ]
    return ParaleloListResponse(paralelos=items)


@router.post(
    "",
    response_model=ParaleloItem,
    status_code=status.HTTP_201_CREATED,
    summary="Crear paralelo",
    description="Crea un nuevo paralelo. Requiere módulo Gestión de Usuarios. El área y el encargado deben existir; el semestre es opcional.",
)
async def crear_paralelo(
    body: ParaleloCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Gestión de Usuarios")),
):
    """Crea un paralelo validando que el área, semestre (si aplica) y encargado existen."""

    # Validar área
    r_area = await db.execute(select(Area).where(Area.id == body.area_id))
    area = r_area.scalar_one_or_none()
    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Área no encontrada",
        )

    # Validar semestre (opcional)
    semestre = None
    if body.semestre_id is not None:
        r_sem = await db.execute(select(Semestre).where(Semestre.id == body.semestre_id))
        semestre = r_sem.scalar_one_or_none()
        if not semestre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Semestre no encontrado",
            )

    # Validar encargado
    r_enc = await db.execute(select(Usuario).where(Usuario.id == body.encargado_id))
    encargado = r_enc.scalar_one_or_none()
    if not encargado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario encargado no encontrado",
        )
    if encargado.estado != "activo":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario debe estar activo para ser asignado como encargado",
        )

    # Validar unicidad (nombre + area_id)
    r_dup = await db.execute(
        select(Paralelo).where(
            Paralelo.nombre == body.nombre,
            Paralelo.area_id == body.area_id,
        )
    )
    if r_dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un paralelo '{body.nombre}' en esa área",
        )

    nuevo = Paralelo(
        nombre=body.nombre,
        area_id=body.area_id,
        semestre_id=body.semestre_id,
        encargado_id=body.encargado_id,
    )
    db.add(nuevo)
    await db.flush()

    return ParaleloItem(
        id=nuevo.id,
        nombre=nuevo.nombre,
        area_id=nuevo.area_id,
        area_nombre=area.nombre,
        semestre_id=nuevo.semestre_id,
        encargado_id=nuevo.encargado_id,
        nombre_encargado=encargado.nombre,
    )


@router.patch(
    "/{paralelo_id}",
    response_model=ParaleloItem,
    summary="Actualizar encargado de un paralelo",
    description="Cambia el encargado de un paralelo existente. Requiere módulo Gestión de Usuarios.",
)
async def actualizar_encargado_paralelo(
    paralelo_id: int,
    body: ParaleloUpdate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Gestión de Usuarios")),
):
    """Actualiza el encargado_id del paralelo indicado."""
    # Verificar que el paralelo existe
    r_paralelo = await db.execute(
        select(Paralelo)
        .options(
            selectinload(Paralelo.encargado),
            selectinload(Paralelo.area),
        )
        .where(Paralelo.id == paralelo_id)
    )
    paralelo = r_paralelo.scalar_one_or_none()
    if not paralelo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paralelo no encontrado",
        )

    # Verificar que el nuevo encargado existe y está activo
    r_usuario = await db.execute(
        select(Usuario).where(Usuario.id == body.encargado_id)
    )
    nuevo_encargado = r_usuario.scalar_one_or_none()
    if not nuevo_encargado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario encargado no encontrado",
        )
    if nuevo_encargado.estado != "activo":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario debe estar activo para ser asignado como encargado",
        )

    paralelo.encargado_id = body.encargado_id
    await db.commit()
    await db.refresh(paralelo)

    return ParaleloItem(
        id=paralelo.id,
        nombre=paralelo.nombre,
        area_id=paralelo.area_id,
        area_nombre=paralelo.area.nombre if paralelo.area else None,
        semestre_id=paralelo.semestre_id,
        encargado_id=paralelo.encargado_id,
        nombre_encargado=nuevo_encargado.nombre,
    )
