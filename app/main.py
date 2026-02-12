"""Punto de entrada de la aplicación FastAPI."""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import router as api_router
from app.core.config import settings
from app.core.database import get_db, init_db
from app.core.security import create_access_token, verify_password
from app.models import *  # noqa: F401, F403 - Registra modelos en Base.metadata antes de init_db
from app.models import Usuario
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.prediccion_service import PrediccionService

logger = logging.getLogger(__name__)

# Documentación Swagger: disponible en /docs (OpenAPI 3.0)
OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Autenticación: login con correo y contraseña. Devuelve un JWT para usar en endpoints protegidos.",
    },
    {
        "name": "api",
        "description": "Endpoints generales de la API v1. Incluye rutas protegidas que requieren JWT.",
    },
    {
        "name": "estudiantes",
        "description": "Tabla de estudiantes por sección: nombre, matrícula, % asistencia, nivel de riesgo.",
    },
    {
        "name": "paralelos",
        "description": "Listado de paralelos (id, nombre, encargado).",
    },
    {
        "name": "materias",
        "description": "Listado de materias (id, nombre).",
    },
    {
        "name": "asistencias",
        "description": "Asistencia del día por materia y paralelo.",
    },
    {
        "name": "usuarios",
        "description": "Listado de usuarios (nombre, correo, rol, estado).",
    },
    {
        "name": "predicciones",
        "description": "Predicción de abandono estudiantil: individual, masiva (Excel), historial, lotes y dashboard.",
    },
    {
        "name": "alertas",
        "description": "Alertas de riesgo de abandono: listado, filtros y actualización de estado.",
    },
    {
        "name": "gestiones",
        "description": "Gestiones académicas: crear, listar y activar períodos académicos.",
    },
    {
        "name": "reportes",
        "description": "Generación de reportes PDF: predictivo general, estudiantes en riesgo, por paralelo, asistencia e individual.",
    },
    {
        "name": "modulos",
        "description": "Módulos del sistema: listado de módulos disponibles para asignación a usuarios.",
    },
    {
        "name": "salud",
        "description": "Comprobación del estado del servicio.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida: inicio y cierre de la aplicación."""
    await init_db()

    # Cargar modelo ML
    try:
        app.state.prediccion_service = PrediccionService(settings.ml_model_dir)
        logger.info("Modelo ML cargado desde '%s'", settings.ml_model_dir)
    except FileNotFoundError:
        logger.warning(
            "No se encontraron artefactos ML en '%s'. "
            "El endpoint de predicciones no estará disponible hasta copiar los .pkl.",
            settings.ml_model_dir,
        )
        app.state.prediccion_service = None

    yield


app = FastAPI(
    title="Sistema Predictivo API",
    description="""
API REST del backend del **Sistema Predictivo** (gestión académica, asistencias y predicción de abandono).

## Cómo usar la documentación (Swagger)

- **Swagger UI:** [GET /docs](/docs) — Interfaz para probar todos los endpoints desde el navegador.
- **ReDoc:** [GET /redoc](/redoc) — Documentación alternativa en formato lectura.
- **OpenAPI JSON:** [GET /openapi.json](/openapi.json) — Esquema en bruto.

## Autenticación (evitar 401)

1. Obtén un token con **POST /api/v1/auth/login** (correo y contraseña). Copia el `access_token` de la respuesta.
2. En Swagger UI, clic en el botón **Authorize** (candado, arriba a la derecha).
3. En el campo **Value** pega solo el token (el texto del access_token, sin escribir "Bearer").
4. Clic en **Authorize** y luego **Close**. Las rutas protegidas enviarán el token y no darán 401.
**Si ves la sección "auth" en Swagger, estás con la versión correcta.**
""",
    version="0.1.0",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True, "tryItOutEnabled": True},
)


def custom_openapi():
    """Asegura que el esquema de seguridad Bearer tenga descripción en Swagger."""
    from fastapi.openapi.utils import get_openapi
    if app.openapi_schema is not None:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Descripción clara para el token en el diálogo Authorize
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
    for name, scheme in openapi_schema["components"]["securitySchemes"].items():
        if scheme.get("type") == "http" and scheme.get("scheme") == "bearer":
            scheme["description"] = "Pegue aquí el access_token obtenido en POST /api/v1/auth/login (solo el token, sin 'Bearer')"
            break
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# CORS: permitir acceso desde cualquier origen (frontend en otro puerto/dominio)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router API (incluye auth y rutas /me, /)
app.include_router(api_router, prefix="/api/v1")


# Login registrado en main para que SIEMPRE aparezca la sección "auth" en /docs
@app.post(
    "/api/v1/auth/login",
    response_model=TokenResponse,
    tags=["auth"],
    summary="Iniciar sesión",
    description="Correo y contraseña. Devuelve un JWT para usar en Authorization: Bearer <token>.",
    responses={
        200: {"description": "Login correcto, se devuelve el access_token"},
        401: {"description": "Correo o contraseña incorrectos"},
        422: {"description": "Datos de entrada inválidos"},
    },
)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Autenticación con correo y contraseña. Devuelve JWT."""
    result = await db.execute(select(Usuario).where(Usuario.email == data.email))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    if not verify_password(data.password, usuario.password_hash or ""):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    token = create_access_token(
        subject=usuario.id,
        extra={"email": usuario.email, "rol_id": usuario.rol_id},
    )
    return TokenResponse(access_token=token, rol_id=usuario.rol_id)


@app.get(
    "/health",
    tags=["salud"],
    summary="Estado del servicio",
    response_description="Indica que la API está en ejecución",
)
async def health_check():
    """Comprueba que el servicio está activo. No requiere autenticación."""
    return {"status": "ok", "message": "Servicio en ejecución"}


@app.get(
    "/debug-carga",
    include_in_schema=False,
)
async def debug_carga():
    """Solo para comprobar qué main.py está cargando el servidor."""
    ruta_main = os.path.abspath(__file__)
    return {
        "archivo_cargado": ruta_main,
        "carpeta": os.path.dirname(ruta_main),
        "correcto": "sistemapredictivoBackend" in ruta_main.replace("\\", "/"),
    }
