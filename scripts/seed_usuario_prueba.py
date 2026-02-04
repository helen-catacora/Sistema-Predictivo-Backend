"""Script para crear un usuario de prueba en la tabla usuarios."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Modulo, Rol, Usuario, UsuarioModulo

# Usuario de prueba (rol Administrador si no existe)
ROL_NOMBRE = "Administrador"
USUARIO_NOMBRE = "Usuario Prueba"
USUARIO_EMAIL = "prueba@sistemapredictivo.edu"
# Contraseña de prueba (se guarda hasheada con bcrypt)
USUARIO_PASSWORD_PLAIN = "1234"


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


async def seed_usuario_prueba():
    password_hash = hash_password(USUARIO_PASSWORD_PLAIN)
    async with AsyncSessionLocal() as session:
        # Obtener o crear rol Administrador
        result = await session.execute(select(Rol).where(Rol.nombre == ROL_NOMBRE))
        rol = result.scalar_one_or_none()
        if not rol:
            rol = Rol(nombre=ROL_NOMBRE)
            session.add(rol)
            await session.flush()
            print(f"  + Rol creado: {ROL_NOMBRE} (id={rol.id})")
        else:
            print(f"  = Rol existente: {ROL_NOMBRE} (id={rol.id})")

        # Crear o actualizar usuario de prueba
        result = await session.execute(select(Usuario).where(Usuario.email == USUARIO_EMAIL))
        usuario = result.scalar_one_or_none()
        if not usuario:
            usuario = Usuario(
                nombre=USUARIO_NOMBRE,
                email=USUARIO_EMAIL,
                password_hash=password_hash,
                rol_id=rol.id,
            )
            session.add(usuario)
            await session.flush()
            print(f"  + Usuario de prueba creado: id={usuario.id}, email={usuario.email}")
        else:
            usuario.password_hash = password_hash
            print(f"  + Contraseña actualizada para: {usuario.email}")

        # Asegurar que existan módulos y asignar todos al usuario de prueba
        result_mod = await session.execute(select(Modulo))
        modulos = result_mod.scalars().all()
        if not modulos:
            for nombre in ("asistencias", "estudiantes", "reportes", "configuracion"):
                session.add(Modulo(nombre=nombre))
            await session.flush()
            result_mod = await session.execute(select(Modulo))
            modulos = result_mod.scalars().all()
        result_um = await session.execute(
            select(UsuarioModulo.modulo_id).where(UsuarioModulo.usuario_id == usuario.id)
        )
        asignados = {row[0] for row in result_um.all()}
        for m in modulos:
            if m.id not in asignados:
                session.add(UsuarioModulo(usuario_id=usuario.id, modulo_id=m.id))
        await session.commit()
    print("Listo.")
    print(f"  Login: {USUARIO_EMAIL} / {USUARIO_PASSWORD_PLAIN}")


if __name__ == "__main__":
    asyncio.run(seed_usuario_prueba())
