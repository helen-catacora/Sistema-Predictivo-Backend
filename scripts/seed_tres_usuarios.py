"""Crea 3 usuarios en la tabla usuarios con contraseña 1234 y todos los módulos asignados."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Modulo, Rol, Usuario, UsuarioModulo

PASSWORD_PLAIN = "1234"

USUARIOS = [
    {"nombre": "Usuario Uno", "email": "usuario1@sistemapredictivo.edu"},
    {"nombre": "Usuario Dos", "email": "usuario2@sistemapredictivo.edu"},
    {"nombre": "Usuario Tres", "email": "usuario3@sistemapredictivo.edu"},
]


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


async def seed_tres_usuarios():
    password_hash = hash_password(PASSWORD_PLAIN)
    async with AsyncSessionLocal() as session:
        # Rol Administrador (o el primero que exista)
        result = await session.execute(select(Rol).limit(1))
        rol = result.scalar_one_or_none()
        if not rol:
            rol = Rol(nombre="Administrador")
            session.add(rol)
            await session.flush()
            print(f"  + Rol creado: {rol.nombre} (id={rol.id})")

        # Asegurar que existan módulos
        result_mod = await session.execute(select(Modulo))
        modulos = result_mod.scalars().all()
        if not modulos:
            for nombre in ("asistencias", "estudiantes", "reportes", "configuracion"):
                session.add(Modulo(nombre=nombre))
            await session.flush()
            result_mod = await session.execute(select(Modulo))
            modulos = result_mod.scalars().all()

        for datos in USUARIOS:
            result = await session.execute(select(Usuario).where(Usuario.email == datos["email"]))
            usuario = result.scalar_one_or_none()
            if not usuario:
                usuario = Usuario(
                    nombre=datos["nombre"],
                    email=datos["email"],
                    password_hash=password_hash,
                    rol_id=rol.id,
                )
                session.add(usuario)
                await session.flush()
                print(f"  + Usuario creado: {datos['email']} (id={usuario.id})")
                # Asignar todos los módulos
                for m in modulos:
                    session.add(UsuarioModulo(usuario_id=usuario.id, modulo_id=m.id))
            else:
                usuario.password_hash = password_hash
                print(f"  = Usuario existente, contraseña actualizada: {datos['email']}")

        await session.commit()

    print("Listo. Contraseña de los 3 usuarios: " + PASSWORD_PLAIN)
    for u in USUARIOS:
        print(f"  - {u['email']}")


if __name__ == "__main__":
    asyncio.run(seed_tres_usuarios())
