"""Servicio de predicción ML para abandono estudiantil."""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa: F401 — necesario para deserializar IterativeImputer


class PrediccionService:
    """Carga los artefactos del modelo v3 (Random Forest + IterativeImputer + OHE) y ejecuta predicciones."""

    NUMERIC_COLS = ["Mat", "Rep", "2T", "Prom", "edad"]
    CATEGORICAL_COLS = [
        "Grado", "Genero", "Semestre", "Carrera",
        "estrato_socioeconomico", "ocupacion_laboral", "con_quien_vive",
        "apoyo_economico", "modalidad_ingreso", "tipo_colegio",
    ]
    VERSION = "v3_iterative_imputer_ohe_rf"

    def __init__(self, model_dir: str) -> None:
        model_path = Path(model_dir)
        self.modelo          = joblib.load(model_path / "mejor_modelo.pkl")
        self.scaler          = joblib.load(model_path / "scaler.pkl")
        self.label_encoders  = joblib.load(model_path / "label_encoders.pkl")
        self.iter_imputer    = joblib.load(model_path / "iter_imputer.pkl")
        self.feature_columns = joblib.load(model_path / "feature_columns.pkl")

    def predecir(self, features: dict) -> tuple[float, str, str]:
        """Predice probabilidad, nivel de riesgo y clasificación para un estudiante."""
        return self.predecir_lote([features])[0]

    def predecir_lote(self, filas: list[dict]) -> list[tuple[float, str, str]]:
        """Predice probabilidad, nivel de riesgo y clasificación para múltiples estudiantes."""
        df = pd.DataFrame(filas)
        df = self._limpiar_texto(df)

        # Paso 1: Label encode categóricas → columnas _enc (enteros o NaN)
        for col in self.CATEGORICAL_COLS:
            enc_col = f"{col}_enc"
            if col in df.columns:
                df[enc_col] = df[col].apply(lambda v, c=col: self._safe_encode(c, v))
            else:
                df[enc_col] = np.nan

        # Paso 2: Construir DataFrame de entrada del IterativeImputer
        # Orden exacto: NUMERIC_COLS + CATEGORICAL_COLS_enc (igual que en entrenamiento)
        imputer_cols = self.NUMERIC_COLS + [f"{c}_enc" for c in self.CATEGORICAL_COLS]
        imputer_input = pd.DataFrame(index=range(len(df)))
        for col in self.NUMERIC_COLS:
            imputer_input[col] = (
                pd.to_numeric(df[col], errors="coerce") if col in df.columns else np.nan
            )
        for col in self.CATEGORICAL_COLS:
            enc_col = f"{col}_enc"
            imputer_input[enc_col] = (
                pd.to_numeric(df[enc_col], errors="coerce") if enc_col in df.columns else np.nan
            )

        # Imputar valores faltantes con IterativeImputer (MICE)
        imputed = self.iter_imputer.transform(imputer_input[imputer_cols].values)
        imputed_df = pd.DataFrame(imputed, columns=imputer_cols)

        # Post-proceso: redondear categóricas al entero válido más cercano
        for col in self.CATEGORICAL_COLS:
            enc_col = f"{col}_enc"
            max_val = len(self.label_encoders[col].classes_) - 1
            imputed_df[enc_col] = imputed_df[enc_col].round().clip(0, max_val).astype(int)
        imputed_df["edad"] = imputed_df["edad"].round().astype(int)

        # Paso 3: Construir pre_ohe — numéricas + categóricas como enteros (sin sufijo _enc)
        # pd.get_dummies las convierte a OHE igual que en el entrenamiento
        pre_ohe = imputed_df[self.NUMERIC_COLS].copy()
        for col in self.CATEGORICAL_COLS:
            pre_ohe[col] = imputed_df[f"{col}_enc"].values

        # One Hot Encoding (drop_first=True, igual que en entrenamiento)
        df_ohe = pd.get_dummies(pre_ohe, columns=self.CATEGORICAL_COLS, drop_first=True)

        # Alinear columnas con las del entrenamiento; rellena con 0 las que no aparezcan
        df_ohe = df_ohe.reindex(columns=self.feature_columns, fill_value=0)

        # Paso 4: Escalar solo numéricas
        df_ohe[self.NUMERIC_COLS] = self.scaler.transform(df_ohe[self.NUMERIC_COLS])

        # Paso 5: Predecir
        X = df_ohe.values
        probas = self.modelo.predict_proba(X)[:, 1]
        clases = self.modelo.predict(X)  # 0 o 1 directamente del modelo

        return [
            (
                round(float(p), 4),
                self.calcular_nivel_riesgo(float(p)),
                "Abandona" if int(c) == 1 else "No Abandona",
            )
            for p, c in zip(probas, clases)
        ]

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
