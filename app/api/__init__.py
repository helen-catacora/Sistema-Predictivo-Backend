"""Routers de la API."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints import (
    alertas,
    asistencias,
    estudiantes,
    gestiones,
    materias,
    modulos,
    paralelos,
    predicciones,
    reportes,
    usuarios,
)
from app.api.endpoints.auth import get_current_user, get_modulos_for_usuario
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models import Usuario
from app.models.role import Rol
from app.schemas.usuario import CambiarContrasenaRequest, PerfilUpdateRequest

router = APIRouter()
# Login está en main.py para que la sección "auth" aparezca en /docs
router.include_router(estudiantes.router)
router.include_router(paralelos.router)
router.include_router(materias.router)
router.include_router(asistencias.router)
router.include_router(usuarios.router)
router.include_router(predicciones.router)
router.include_router(alertas.router)
router.include_router(gestiones.router)
router.include_router(reportes.router)
router.include_router(modulos.router)


@router.get(
    "/me",
    tags=["api"],
    summary="Usuario actual (protegido)",
    response_description="Datos completos del usuario autenticado",
    responses={
        200: {"description": "Usuario obtenido correctamente"},
        401: {"description": "Token no enviado, inválido o expirado"},
    },
)
async def get_me(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Devuelve el usuario actual a partir del JWT, incluyendo datos personales,
    rol, estado y módulos a los que tiene acceso.
    **Requiere:** header `Authorization: Bearer <access_token>`.
    """
    modulos = await get_modulos_for_usuario(db, current_user.id)
    # Obtener nombre del rol
    r = await db.execute(select(Rol.nombre).where(Rol.id == current_user.rol_id))
    rol_nombre = r.scalar_one_or_none() or ""
    return {
        "id": current_user.id,
        "nombre": current_user.nombre,
        "email": current_user.email,
        "rol_id": current_user.rol_id,
        "rol_nombre": rol_nombre,
        "estado": current_user.estado,
        "carnet_identidad": current_user.carnet_identidad,
        "telefono": current_user.telefono,
        "cargo": current_user.cargo,
        "modulos": modulos,
    }


@router.patch(
    "/me",
    tags=["api"],
    summary="Actualizar perfil propio",
    responses={
        200: {"description": "Perfil actualizado correctamente"},
        401: {"description": "Token no enviado, inválido o expirado"},
    },
)
async def update_me(
    body: PerfilUpdateRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permite al usuario autenticado actualizar su propio perfil
    (nombre, carnet_identidad, telefono, cargo). Solo se modifican
    los campos enviados (no nulos).
    """
    campos_actualizados = body.model_dump(exclude_none=True)
    if not campos_actualizados:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe enviar al menos un campo para actualizar.",
        )
    for campo, valor in campos_actualizados.items():
        setattr(current_user, campo, valor)
    await db.flush()
    # Obtener nombre del rol para la respuesta
    r = await db.execute(select(Rol.nombre).where(Rol.id == current_user.rol_id))
    rol_nombre = r.scalar_one_or_none() or ""
    return {
        "message": "Perfil actualizado correctamente",
        "usuario": {
            "id": current_user.id,
            "nombre": current_user.nombre,
            "email": current_user.email,
            "rol_id": current_user.rol_id,
            "rol_nombre": rol_nombre,
            "estado": current_user.estado,
            "carnet_identidad": current_user.carnet_identidad,
            "telefono": current_user.telefono,
            "cargo": current_user.cargo,
        },
    }


@router.post(
    "/me/cambiar-contrasena",
    tags=["api"],
    summary="Cambiar contraseña propia",
    responses={
        200: {"description": "Contraseña actualizada correctamente"},
        400: {"description": "Contraseña actual incorrecta"},
        401: {"description": "Token no enviado, inválido o expirado"},
    },
)
async def cambiar_contrasena(
    body: CambiarContrasenaRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permite al usuario autenticado cambiar su contraseña.
    Requiere la contraseña actual para verificar identidad.
    """
    if not verify_password(body.contrasena_actual, current_user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta.",
        )
    current_user.password_hash = hash_password(body.contrasena_nueva)
    await db.flush()
    return {"message": "Contraseña actualizada correctamente"}


@router.get(
    "/",
    tags=["api"],
    summary="Raíz de la API v1",
    response_description="Mensaje de bienvenida y enlace a la documentación",
)
async def api_root():
    """Información básica de la API y enlace a la documentación Swagger."""
    return {"message": "Sistema Predictivo API v1", "docs": "/docs", "redoc": "/redoc"}
