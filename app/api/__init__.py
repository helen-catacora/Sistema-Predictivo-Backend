"""Routers de la API."""
from fastapi import APIRouter

# Importar y registrar routers aquí
# from app.api.endpoints import items
# router.include_router(items.router, prefix="/items", tags=["items"])

router = APIRouter()


@router.get("/")
async def api_root():
    """Raíz de la API v1."""
    return {"message": "Sistema Predictivo API v1", "docs": "/docs"}
