"""Esquemas para autenticación y JWT."""
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Body del endpoint de login."""

    email: EmailStr = Field(description="Correo electrónico del usuario", examples=["prueba@sistemapredictivo.edu"])
    password: str = Field(description="Contraseña en texto plano", min_length=1, examples=["1234"])


class TokenResponse(BaseModel):
    """Respuesta con access_token JWT y datos del usuario."""

    access_token: str = Field(description="Token JWT para enviar en header Authorization: Bearer <token>")
    token_type: str = Field(default="bearer", description="Tipo de token (siempre 'bearer')")
    rol_id: int = Field(description="ID del rol del usuario autenticado")


class TokenPayload(BaseModel):
    """Datos que viajan dentro del JWT (para dependencia get_current_user)."""
    sub: str
    email: str | None = None
    rol_id: int | None = None
