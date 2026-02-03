"""Punto de entrada de la aplicación FastAPI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import init_db
from app.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida: inicio y cierre de la aplicación."""
    # Startup: inicializar conexión a base de datos, etc.
    await init_db()
    yield
    # Shutdown: cerrar conexiones, limpiar recursos
    pass


app = FastAPI(
    title="Sistema Predictivo API",
    description="API del backend del sistema predictivo",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1", tags=["api"])


@app.get("/health")
async def health_check():
    """Endpoint de salud para verificar que el servicio está activo."""
    return {"status": "ok", "message": "Servicio en ejecución"}
