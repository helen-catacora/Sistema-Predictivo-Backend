import os
import requests
import joblib

MODEL_DIR = "ml_models"
os.makedirs(MODEL_DIR, exist_ok=True)


def download_file(url: str, filename: str):
    """Descarga un archivo desde una URL."""
    path = os.path.join(MODEL_DIR, filename)

    if os.path.exists(path):
        print(f"✔ Modelo ya existe: {filename}")
        return path

    print(f"⬇ Descargando modelo: {filename}")
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Error descargando {filename}")

    with open(path, "wb") as f:
        f.write(response.content)

    return path


def load_model(url: str, filename: str):
    """Descarga y carga un modelo."""
    path = download_file(url, filename)
    model = joblib.load(path)
    print(f"Modelo cargado: {filename}")
    return model