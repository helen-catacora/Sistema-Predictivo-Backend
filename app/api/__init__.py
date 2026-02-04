"""Routers de la API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.endpoints import asistencias, estudiantes, materias, paralelos, usuarios
from app.api.endpoints.auth import get_current_user, get_modulos_for_usuario
from app.core.database import get_db
from app.models import Usuario

router = APIRouter()
# Login está en main.py para que la sección "auth" aparezca en /docs
router.include_router(estudiantes.router)
router.include_router(paralelos.router)
router.include_router(materias.router)
router.include_router(asistencias.router)
router.include_router(usuarios.router)


@router.get(
    "/me",
    tags=["api"],
    summary="Usuario actual (protegido)",
    response_description="Datos del usuario autenticado (id, nombre, email, rol_id, estado, modulos)",
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
    Devuelve el usuario actual a partir del JWT, incluyendo estado y módulos a los que tiene acceso.
    **Requiere:** header `Authorization: Bearer <access_token>` (obtener el token con POST /api/v1/auth/login).
    """
    modulos = await get_modulos_for_usuario(db, current_user.id)
    return {
        "id": current_user.id,
        "nombre": current_user.nombre,
        "email": current_user.email,
        "rol_id": current_user.rol_id,
        "estado": current_user.estado,
        "modulos": modulos,
    }


@router.get(
    "/",
    tags=["api"],
    summary="Raíz de la API v1",
    response_description="Mensaje de bienvenida y enlace a la documentación",
)
async def api_root():
    """Información básica de la API y enlace a la documentación Swagger."""
    return {"message": "Sistema Predictivo API v1", "docs": "/docs", "redoc": "/redoc"}
