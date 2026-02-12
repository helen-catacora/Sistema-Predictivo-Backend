"""Esquemas para listado y creación de usuarios."""
from pydantic import BaseModel, EmailStr, Field, field_validator


class UsuarioCreate(BaseModel):
    """Body para crear un nuevo usuario. Al crear, estado queda en inactivo."""

    nombre: str = Field(description="Nombre del usuario", min_length=1)
    carnet_identidad: str | None = Field(default=None, description="Carnet de identidad")
    telefono: str | None = Field(default=None, description="Teléfono")
    cargo: str | None = Field(default=None, description="Cargo")
    correo: EmailStr = Field(description="Correo electrónico (único)")
    contraseña: str = Field(description="Contraseña en texto", min_length=1)
    rol_id: int = Field(description="ID del rol del usuario")
    modulos: list[int] | None = Field(
        default=None,
        description="Lista de IDs de módulos a asignar. Opcional; si no se envía, el usuario se crea sin módulos.",
    )


class UsuarioUpdateEstadoModulos(BaseModel):
    """Body para actualizar datos del usuario: nombre, carnet, teléfono, cargo, correo, rol, estado y módulos. Todos opcionales."""

    nombre: str | None = Field(default=None, description="Nombre del usuario. Si no se envía, no se modifica.")
    carnet_identidad: str | None = Field(default=None, description="Carnet de identidad.")
    telefono: str | None = Field(default=None, description="Teléfono.")
    cargo: str | None = Field(default=None, description="Cargo.")
    correo: EmailStr | None = Field(default=None, description="Correo electrónico (único). Si no se envía, no se modifica.")
    rol_id: int | None = Field(default=None, description="ID del rol. Si no se envía, no se modifica.")
    estado: str | None = Field(
        default=None,
        description="Estado: activo o inactivo. Si no se envía, no se modifica.",
    )
    modulos: list[int] | None = Field(
        default=None,
        description="Lista de IDs de módulos a los que tendrá acceso. Reemplaza la asignación actual. Si no se envía, no se modifican.",
    )

    @field_validator("estado")
    @classmethod
    def estado_valido(cls, v: str | None) -> str | None:
        if v is not None and v not in ("activo", "inactivo"):
            raise ValueError("estado debe ser 'activo' o 'inactivo'")
        return v


class UsuarioListItem(BaseModel):
    """Fila de usuario en el listado: nombre, correo, rol y estado."""

    id: int = Field(description="ID del usuario")
    nombre: str = Field(description="Nombre del usuario")
    correo: str = Field(description="Correo electrónico")
    rol: str = Field(description="Nombre del rol (ej. Administrador)")
    estado: str = Field(description="Estado: activo o inactivo")
    modulos: list[int] = Field(default_factory=list, description="IDs de los módulos asignados al usuario")


class UsuarioListResponse(BaseModel):
    """Respuesta del listado de usuarios."""

    usuarios: list[UsuarioListItem] = Field(description="Lista de usuarios")


class PerfilUpdateRequest(BaseModel):
    """Body para que el usuario actualice su propio perfil."""

    nombre: str | None = Field(default=None, description="Nombre del usuario", min_length=1)
    carnet_identidad: str | None = Field(default=None, description="Carnet de identidad")
    telefono: str | None = Field(default=None, description="Teléfono")
    cargo: str | None = Field(default=None, description="Cargo")


class CambiarContrasenaRequest(BaseModel):
    """Body para cambiar la contraseña del usuario autenticado."""

    contrasena_actual: str = Field(description="Contraseña actual")
    contrasena_nueva: str = Field(description="Nueva contraseña", min_length=6)
