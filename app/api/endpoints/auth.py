"""Endpoints de autenticación: login y dependencia para proteger rutas."""
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import create_access_token, decode_access_token, verify_password
from app.models import Modulo, Usuario, UsuarioModulo
from app.schemas.auth import LoginRequest, TokenResponse

# Solo este rol tiene acceso a todos los módulos sin restricción por usuario_modulo
ROL_SUPERADMIN = "Super Administrador"

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    response_description="Token JWT para usar en el header Authorization",
    responses={
        200: {"description": "Login correcto, se devuelve el access_token"},
        401: {"description": "Correo o contraseña incorrectos"},
        422: {"description": "Datos de entrada inválidos (ej. email mal formado)"},
    },
)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Autenticación con **correo** y **contraseña**.
    Si las credenciales son correctas, devuelve un **access_token** (JWT).
    Usa ese token en el header `Authorization: Bearer <access_token>` para acceder a rutas protegidas (ej. GET /api/v1/me).
    """
    result = await db.execute(select(Usuario).where(Usuario.email == data.email))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    if not verify_password(data.password, usuario.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    if usuario.estado != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacte al administrador.",
        )
    token = create_access_token(
        subject=usuario.id,
        extra={"email": usuario.email, "rol_id": usuario.rol_id},
    )
    return TokenResponse(access_token=token, rol_id=usuario.rol_id)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    """Dependencia: exige un JWT válido y devuelve el usuario actual. Usar en endpoints protegidos."""
    if not credentials or credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación no proporcionado o inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload["sub"]
    result = await db.execute(select(Usuario).where(Usuario.id == int(user_id)))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if usuario.estado != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacte al administrador.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


async def get_modulos_for_usuario(db: AsyncSession, usuario_id: int) -> list[str]:
    """Devuelve la lista de nombres de módulos a los que tiene acceso el usuario.
    Si el usuario tiene rol Superadministrador, devuelve todos los módulos."""
    # Cargar usuario con rol para ver si es Superadministrador
    q_user = (
        select(Usuario)
        .options(selectinload(Usuario.rol))
        .where(Usuario.id == usuario_id)
    )
    r_user = await db.execute(q_user)
    usuario = r_user.scalar_one_or_none()
    if usuario and usuario.rol and usuario.rol.nombre == ROL_SUPERADMIN:
        # Superadministrador: acceso a todos los módulos
        r_all = await db.execute(select(Modulo.nombre))
        return [row[0] for row in r_all.all()]

    q = (
        select(Modulo.nombre)
        .join(UsuarioModulo, UsuarioModulo.modulo_id == Modulo.id)
        .where(UsuarioModulo.usuario_id == usuario_id)
    )
    r = await db.execute(q)
    return [row[0] for row in r.all()]


def require_module(nombre_modulo: str) -> Callable:
    """Dependencia que exige que el usuario actual tenga acceso al módulo indicado."""

    async def _check(
        current_user: Usuario = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> Usuario:
        modulos = await get_modulos_for_usuario(db, current_user.id)
        if nombre_modulo not in modulos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tiene acceso al módulo '{nombre_modulo}'",
            )
        return current_user

    return _check
