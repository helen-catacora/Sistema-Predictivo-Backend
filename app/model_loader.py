"""Descarga y upload de artefactos ML desde/hacia Supabase Storage y Google Drive."""
import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Artefactos que siempre vienen de Supabase Storage
_ARTEFACTOS_SUPABASE = [
    "mejor_modelo.pkl",
    "scaler.pkl",
    "label_encoders.pkl",
    "feature_columns.pkl",
]

# Artefacto con fallback a Google Drive (por tamaño)
_ARTEFACTO_GDRIVE = "iter_imputer.pkl"


def _url_publica_supabase(project_url: str, bucket: str, filename: str) -> str:
    return f"{project_url.rstrip('/')}/storage/v1/object/public/{bucket}/{filename}"


def _descargar_desde_supabase(project_url: str, bucket: str, filename: str, destino: Path) -> bool:
    """Descarga un archivo desde Supabase Storage público. Retorna True si tuvo éxito."""
    url = _url_publica_supabase(project_url, bucket, filename)
    try:
        with requests.get(url, stream=True, timeout=120) as resp:
            if resp.status_code == 200:
                with open(destino, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8 * 1024 * 1024):
                        f.write(chunk)
                logger.info("Descargado desde Supabase: %s", filename)
                return True
            logger.debug("Supabase respondió %s para %s", resp.status_code, filename)
            return False
    except Exception as exc:
        logger.warning("Error al descargar %s desde Supabase: %s", filename, exc)
        return False


def _descargar_desde_gdrive(file_id: str, destino: Path) -> None:
    """Descarga un archivo desde Google Drive usando gdown (maneja archivos grandes)."""
    import gdown  # import local para no fallar en entornos sin gdown

    url = f"https://drive.google.com/uc?id={file_id}"
    logger.info("Descargando iter_imputer.pkl desde Google Drive...")
    gdown.download(url, str(destino), quiet=False, fuzzy=True)
    if not destino.exists() or destino.stat().st_size == 0:
        raise RuntimeError("La descarga desde Google Drive produjo un archivo vacío o fallida.")
    logger.info("Descargado desde Google Drive: %s", destino.name)


def descargar_artefactos_ml(model_dir: str, config) -> None:
    """Descarga los 5 artefactos .pkl y model_info.json al directorio model_dir si no existen ya.

    - 4 .pkl + model_info.json se descargan desde Supabase Storage (bucket público).
    - iter_imputer.pkl: primero intenta Supabase; si no está, usa Google Drive.

    Si supabase_project_url está vacío, se omite la descarga (entorno local con .pkl ya presentes).
    """
    if not config.supabase_project_url:
        logger.info("SUPABASE_PROJECT_URL no configurado — se omite descarga de artefactos ML.")
        return

    model_path = Path(model_dir)
    model_path.mkdir(parents=True, exist_ok=True)

    # Descargar los 4 artefactos .pkl desde Supabase
    for filename in _ARTEFACTOS_SUPABASE:
        destino = model_path / filename
        if destino.exists():
            logger.info("Artefacto ya existe localmente: %s", filename)
            continue
        ok = _descargar_desde_supabase(
            config.supabase_project_url,
            config.supabase_storage_bucket,
            filename,
            destino,
        )
        if not ok:
            raise RuntimeError(f"No se pudo descargar {filename} desde Supabase Storage.")

    # Descargar model_info.json (métricas del modelo actual — opcional, no falla si no existe)
    info_destino = model_path / "model_info.json"
    if not info_destino.exists():
        _descargar_desde_supabase(
            config.supabase_project_url,
            config.supabase_storage_bucket,
            "model_info.json",
            info_destino,
        )

    # Descargar iter_imputer.pkl: Supabase primero, Google Drive como fallback
    destino = model_path / _ARTEFACTO_GDRIVE
    if destino.exists():
        logger.info("Artefacto ya existe localmente: %s", _ARTEFACTO_GDRIVE)
        return

    ok = _descargar_desde_supabase(
        config.supabase_project_url,
        config.supabase_storage_bucket,
        _ARTEFACTO_GDRIVE,
        destino,
    )
    if not ok:
        if not config.gdrive_iter_imputer_id:
            raise RuntimeError(
                "iter_imputer.pkl no está en Supabase y GDRIVE_ITER_IMPUTER_ID no está configurado."
            )
        _descargar_desde_gdrive(config.gdrive_iter_imputer_id, destino)


def subir_artefactos_a_supabase(model_dir: str, config) -> None:
    """Sube los 5 artefactos .pkl desde model_dir hacia Supabase Storage.

    Se usa después de aceptar un modelo nuevo, para que el siguiente reinicio
    descargue el modelo actualizado (el filesystem de Render es efímero).

    Si supabase_project_url o supabase_service_role_key están vacíos, se omite silenciosamente.
    """
    if not config.supabase_project_url or not config.supabase_service_role_key:
        logger.warning(
            "SUPABASE_PROJECT_URL o SUPABASE_SERVICE_ROLE_KEY no configurados — "
            "los artefactos aceptados NO se subirán a Supabase. "
            "Se perderán al reiniciar el servidor."
        )
        return

    model_path = Path(model_dir)
    todos = _ARTEFACTOS_SUPABASE + [_ARTEFACTO_GDRIVE, "model_info.json"]
    headers = {
        "Authorization": f"Bearer {config.supabase_service_role_key}",
        "Content-Type": "application/octet-stream",
    }

    for filename in todos:
        ruta = model_path / filename
        if not ruta.exists():
            logger.warning("No se encontró %s para subir a Supabase.", filename)
            continue

        url = (
            f"{config.supabase_project_url.rstrip('/')}/storage/v1/object/"
            f"{config.supabase_storage_bucket}/{filename}"
        )
        try:
            with open(ruta, "rb") as f:
                resp = requests.put(url, data=f, headers=headers, timeout=300)
            if resp.status_code in (200, 201):
                logger.info("Subido a Supabase: %s", filename)
            else:
                logger.warning(
                    "Error al subir %s a Supabase: HTTP %s — %s",
                    filename,
                    resp.status_code,
                    resp.text[:200],
                )
        except Exception as exc:
            logger.warning("Excepción al subir %s a Supabase: %s", filename, exc)
