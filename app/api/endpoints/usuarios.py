"""Endpoints para listado y creación de usuarios."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.auth import require_module
from app.core.database import get_db
from app.core.security import hash_password
from app.models import Modulo, Rol, Usuario, UsuarioModulo
from app.schemas.usuario import (
    UsuarioCreate,
    UsuarioListItem,
    UsuarioListResponse,
    UsuarioUpdateEstadoModulos,
)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get(
    "",
    response_model=UsuarioListResponse,
    summary="Listar usuarios",
    description="Lista todos los usuarios con nombre, correo, rol, estado y módulos asignados (IDs). Requiere módulo Gestión de Usuarios.",
)
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Gestión de Usuarios")),
):
    """Devuelve los usuarios con nombre, correo, nombre del rol y estado."""
    q = (
        select(Usuario)
        .options(selectinload(Usuario.rol), selectinload(Usuario.modulos))
        .order_by(Usuario.nombre)
    )
    result = await db.execute(q)
    usuarios = result.scalars().unique().all()

    items = [
        UsuarioListItem(
            id=u.id,
            nombre=u.nombre,
            correo=u.email,
            rol=u.rol.nombre if u.rol else "",
            estado=u.estado,
            modulos=[m.id for m in u.modulos],
        )
        for u in usuarios
    ]
    return UsuarioListResponse(usuarios=items)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
    description="Crea un nuevo usuario. Estado inicial: inactivo. Campo modulos acepta lista de IDs de módulos. Requiere módulo Gestión de Usuarios.",
)
async def crear_usuario(
    body: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Gestión de Usuarios")),
):
    """Crea un usuario con los datos del body. El estado se establece en inactivo."""
    # Correo único
    r = await db.execute(select(Usuario).where(Usuario.email == body.correo))
    if r.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese correo",
        )
    # Rol debe existir
    r_rol = await db.execute(select(Rol).where(Rol.id == body.rol_id))
    if not r_rol.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol indicado no existe",
        )

    usuario = Usuario(
        nombre=body.nombre,
        email=body.correo,
        password_hash=hash_password(body.contraseña),
        rol_id=body.rol_id,
        estado="inactivo",
        carnet_identidad=body.carnet_identidad,
        telefono=body.telefono,
        cargo=body.cargo,
    )
    db.add(usuario)
    await db.flush()

    # Asignar módulos si se enviaron
    modulos_asignados: list[int] = []
    if body.modulos:
        r_mod = await db.execute(select(Modulo).where(Modulo.id.in_(body.modulos)))
        modulos_encontrados = r_mod.scalars().all()
        ids_encontrados = {m.id for m in modulos_encontrados}
        faltantes = set(body.modulos) - ids_encontrados
        if faltantes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Módulos no existentes (IDs): {sorted(faltantes)}",
            )
        for m in modulos_encontrados:
            db.add(UsuarioModulo(usuario_id=usuario.id, modulo_id=m.id))
        modulos_asignados = body.modulos

    await db.commit()
    await db.refresh(usuario)
    return {"id": usuario.id, "correo": usuario.email, "estado": usuario.estado, "modulos": modulos_asignados}


@router.patch(
    "/{usuario_id}",
    summary="Actualizar usuario",
    description="Actualiza nombre, carnet, teléfono, cargo, correo, rol_id, estado y/o módulos (IDs). Solo los campos enviados se modifican. Requiere módulo Gestión de Usuarios.",
)
async def actualizar_estado_y_modulos(
    usuario_id: int,
    body: UsuarioUpdateEstadoModulos,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(require_module("Gestión de Usuarios")),
):
    """Actualiza los campos enviados del usuario (nombre, carnet, teléfono, cargo, correo, rol_id, estado, módulos)."""
    r = await db.execute(
        select(Usuario).where(Usuario.id == usuario_id)
    )
    usuario = r.scalar_one_or_none()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if body.nombre is not None:
        usuario.nombre = body.nombre
    if body.carnet_identidad is not None:
        usuario.carnet_identidad = body.carnet_identidad
    if body.telefono is not None:
        usuario.telefono = body.telefono
    if body.cargo is not None:
        usuario.cargo = body.cargo
    if body.correo is not None:
        otro = await db.execute(select(Usuario).where(Usuario.email == body.correo, Usuario.id != usuario_id))
        if otro.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otro usuario con ese correo",
            )
        usuario.email = body.correo
    if body.rol_id is not None:
        r_rol = await db.execute(select(Rol).where(Rol.id == body.rol_id))
        if not r_rol.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El rol indicado no existe",
            )
        usuario.rol_id = body.rol_id
    if body.estado is not None:
        usuario.estado = body.estado

    if body.modulos is not None:
        await db.execute(delete(UsuarioModulo).where(UsuarioModulo.usuario_id == usuario_id))
        if body.modulos:
            r_mod = await db.execute(select(Modulo).where(Modulo.id.in_(body.modulos)))
            modulos = r_mod.scalars().all()
            ids_encontrados = {m.id for m in modulos}
            faltantes = set(body.modulos) - ids_encontrados
            if faltantes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Módulos no existentes (IDs): {sorted(faltantes)}",
                )
            for m in modulos:
                db.add(UsuarioModulo(usuario_id=usuario_id, modulo_id=m.id))

    await db.commit()
    await db.refresh(usuario)

    modulos_actuales: list[int] = []
    if body.modulos is not None:
        modulos_actuales = body.modulos
    else:
        r_um = await db.execute(
            select(Modulo.id)
            .join(UsuarioModulo, UsuarioModulo.modulo_id == Modulo.id)
            .where(UsuarioModulo.usuario_id == usuario_id)
        )
        modulos_actuales = [row[0] for row in r_um.all()]

    return {
        "id": usuario.id,
        "estado": usuario.estado,
        "modulos": modulos_actuales,
    }
