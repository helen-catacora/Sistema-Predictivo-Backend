"""Servicio de predicción ML para abandono estudiantil."""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


class PrediccionService:
    """Carga los artefactos del modelo XGBoost y ejecuta predicciones."""

    NUMERIC_COLS = ["Mat", "Rep", "2T", "Prom", "edad"]
    CATEGORICAL_COLS = [
        "Grado", "Genero", "Semestre", "Carrera",
        "estrato_socioeconomico", "ocupacion_laboral", "con_quien_vive",
        "apoyo_economico", "modalidad_ingreso", "tipo_colegio",
    ]
    FEATURE_COLS = [
        "Mat", "Rep", "2T", "Prom", "edad",
        "Grado_enc", "Genero_enc", "Semestre_enc", "Carrera_enc",
        "estrato_socioeconomico_enc", "ocupacion_laboral_enc",
        "con_quien_vive_enc", "apoyo_economico_enc",
        "modalidad_ingreso_enc", "tipo_colegio_enc",
    ]
    VERSION = "v2_con_imputacion_knn"

    def __init__(self, model_dir: str) -> None:
        model_path = Path(model_dir)
        self.modelo = joblib.load(model_path / "mejor_modelo.pkl")
        self.scaler = joblib.load(model_path / "scaler.pkl")
        self.label_encoders: dict = joblib.load(model_path / "label_encoders.pkl")
        self.knn_imputer = joblib.load(model_path / "knn_imputer.pkl")

    def predecir(self, features: dict) -> tuple[float, str]:
        """Predice probabilidad de abandono para un estudiante."""
        resultados = self.predecir_lote([features])
        return resultados[0]

    def predecir_lote(self, filas: list[dict]) -> list[tuple[float, str]]:
        """Predice probabilidad de abandono para múltiples estudiantes."""
        df = pd.DataFrame(filas)
        df = self._limpiar_texto(df)

        # Paso 1: Label encode categóricas
        for col in self.CATEGORICAL_COLS:
            enc_col = f"{col}_enc"
            if col in df.columns:
                df[enc_col] = df[col].apply(
                    lambda v, c=col: self._safe_encode(c, v)
                )
            else:
                df[enc_col] = np.nan

        # Construir DataFrame con features en el orden correcto
        feature_df = pd.DataFrame()
        for col in self.FEATURE_COLS:
            if col in df.columns:
                feature_df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                feature_df[col] = np.nan

        # Paso 2: KNN impute datos faltantes
        imputed = self.knn_imputer.transform(feature_df.values)
        feature_df = pd.DataFrame(imputed, columns=self.FEATURE_COLS)

        # Redondear categóricas codificadas al entero más cercano
        for col in self.FEATURE_COLS:
            if col.endswith("_enc"):
                feature_df[col] = feature_df[col].round().astype(int)

        # Paso 3: Scale solo numéricas
        feature_df[self.NUMERIC_COLS] = self.scaler.transform(
            feature_df[self.NUMERIC_COLS]
        )

        # Paso 4: Predecir
        probas = self.modelo.predict_proba(feature_df)[:, 1]

        resultados = []
        for prob in probas:
            prob_float = round(float(prob), 4)
            nivel = self.calcular_nivel_riesgo(prob_float)
            resultados.append((prob_float, nivel))

        return resultados

    @staticmethod
    def calcular_nivel_riesgo(probabilidad: float) -> str:
        """Calcula nivel de riesgo: <0.3 Bajo, 0.3-0.5 Medio, 0.5-0.7 Alto, >=0.7 Critico."""
        if probabilidad >= 0.7:
            return "Critico"
        elif probabilidad >= 0.5:
            return "Alto"
        elif probabilidad >= 0.3:
            return "Medio"
        else:
            return "Bajo"

    def _safe_encode(self, col: str, value) -> float:
        """Codifica un valor categórico; retorna NaN si es nulo o desconocido."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return np.nan
        try:
            encoder = self.label_encoders[col]
            return float(encoder.transform([value])[0])
        except (ValueError, KeyError):
            return np.nan

    @staticmethod
    def _limpiar_texto(df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza texto para coincidir con el label encoder."""
        reemplazos = {
            "Carrera": {
                "Tecnológicas": "Tecnologicas",
                "No Tecnológicas": "No Tecnologicas",
            },
            "tipo_colegio": {"Público": "Publico"},
            "modalidad_ingreso": {
                "Prueba de Suficiencia Académica": "Prueba de Suficiencia Academica",
                "Admisión Especial": "Admision Especial",
            },
        }
        for col, mapeo in reemplazos.items():
            if col in df.columns:
                df[col] = df[col].replace(mapeo)
        return df
