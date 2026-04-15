"""Servicio de predicción ML para abandono estudiantil."""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa: F401 — necesario para deserializar IterativeImputer

_LABELS_FEATURES = {
    "Mat": "Materias cursadas",
    "Rep": "Materias reprobadas",
    "2T": "Materias en 2do turno",
    "Prom": "Promedio académico",
    "edad": "Edad",
    "Grado": "Grado",
    "Genero": "Género",
    "Semestre": "Semestre",
    "Carrera": "Carrera",
    "estrato_socioeconomico": "Estrato socioeconómico",
    "ocupacion_laboral": "Situación laboral",
    "con_quien_vive": "Con quién vive",
    "apoyo_economico": "Apoyo económico",
    "modalidad_ingreso": "Modalidad de ingreso",
    "tipo_colegio": "Tipo de colegio",
}


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
        self._explainer = None  # se inicializa en primer uso de explicar_shap

    def predecir(self, features: dict) -> tuple[float, str, str]:
        """Predice probabilidad, nivel de riesgo y clasificación para un estudiante."""
        return self.predecir_lote([features])[0]

    def predecir_lote(self, filas: list[dict]) -> list[tuple[float, str, str]]:
        """Predice probabilidad, nivel de riesgo y clasificación para múltiples estudiantes."""
        df_ohe = self._preprocesar(filas)
        X = df_ohe.values
        probas = self.modelo.predict_proba(X)[:, 1]
        clases = self.modelo.predict(X)

        return [
            (
                round(float(p), 4),
                self.calcular_nivel_riesgo(float(p)),
                "Abandona" if int(c) == 1 else "No Abandona",
            )
            for p, c in zip(probas, clases)
        ]

    def explicar_shap(self, features: dict, top_n: int = 5) -> list[dict]:
        """Retorna los top_n factores que más contribuyen a la predicción del estudiante.

        Cada elemento: {nombre, valor, contribucion, tipo}
          - contribucion > 0 → empuja hacia abandono (tipo='riesgo')
          - contribucion < 0 → reduce riesgo (tipo='protector')
        """
        try:
            import shap  # importación lazy para no romper si no está instalado
        except ImportError:
            return []

        if self._explainer is None:
            self._explainer = shap.TreeExplainer(self.modelo)

        df_ohe = self._preprocesar([features])

        sv = self._explainer.shap_values(df_ohe)
        # RF binario: sv puede ser lista [clase0, clase1], ndarray 3D, o ndarray 2D (SHAP >= 0.50)
        if isinstance(sv, list):
            shap_row = sv[1][0]      # lista [class0, class1] → clase 1, muestra 0
        elif sv.ndim == 3:
            shap_row = sv[0, :, 1]  # 3D (n_samples, n_features, n_classes) → clase 1
        else:
            shap_row = sv[0]         # 2D (n_samples, n_features) → SHAP v0.50+ clase positiva directa

        # Agrupar columnas OHE por feature original
        # Ej: Carrera_1, Carrera_2 → sumar contribuciones → "Carrera"
        grupos: dict[str, float] = {}
        for col, val in zip(self.feature_columns, shap_row):
            if col in self.NUMERIC_COLS:
                grupos[col] = grupos.get(col, 0) + float(val)
            else:
                parent = "_".join(col.split("_")[:-1])
                grupos[parent] = grupos.get(parent, 0) + float(val)

        # Ordenar por |contribución| descendente y tomar top_n
        ordenados = sorted(grupos.items(), key=lambda x: abs(x[1]), reverse=True)[:top_n]

        resultado = []
        for feat, contrib in ordenados:
            val_usado = features.get(feat)
            resultado.append({
                "nombre": _LABELS_FEATURES.get(feat, feat),
                "valor": str(val_usado) if val_usado is not None else "N/D",
                "contribucion": round(contrib, 4),
                "tipo": "riesgo" if contrib > 0 else "protector",
            })
        return resultado

    def importancias_globales(self, top_n: int = 8) -> list[dict]:
        """Retorna las top_n variables más importantes del modelo (global, no por estudiante)."""
        fi = self.modelo.feature_importances_
        grupos: dict[str, float] = {}
        for col, imp in zip(self.feature_columns, fi):
            if col in self.NUMERIC_COLS:
                grupos[col] = grupos.get(col, 0) + float(imp)
            else:
                parent = "_".join(col.split("_")[:-1])
                grupos[parent] = grupos.get(parent, 0) + float(imp)

        top = sorted(grupos.items(), key=lambda x: -x[1])[:top_n]
        return [
            {"feature": _LABELS_FEATURES.get(k, k), "importancia": round(v * 100, 1)}
            for k, v in top
        ]

    def _preprocesar(self, filas: list[dict]) -> pd.DataFrame:
        """Ejecuta el pipeline completo label encode → impute → OHE → scale.
        Retorna el DataFrame listo para predict / shap_values."""
        df = pd.DataFrame(filas)
        df = self._limpiar_texto(df)

        # Paso 1: Label encode categóricas → columnas _enc
        for col in self.CATEGORICAL_COLS:
            enc_col = f"{col}_enc"
            if col in df.columns:
                df[enc_col] = df[col].apply(lambda v, c=col: self._safe_encode(c, v))
            else:
                df[enc_col] = np.nan

        # Paso 2: DataFrame de entrada del IterativeImputer
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

        imputed = self.iter_imputer.transform(imputer_input[imputer_cols])
        imputed_df = pd.DataFrame(imputed, columns=imputer_cols)

        # Post-proceso: redondear categóricas al entero válido más cercano
        for col in self.CATEGORICAL_COLS:
            enc_col = f"{col}_enc"
            max_val = len(self.label_encoders[col].classes_) - 1
            imputed_df[enc_col] = imputed_df[enc_col].round().clip(0, max_val).astype(int)
        imputed_df["edad"] = imputed_df["edad"].round().astype(int)

        # Paso 3: pre_ohe — numéricas + categóricas como enteros
        pre_ohe = imputed_df[self.NUMERIC_COLS].copy()
        for col in self.CATEGORICAL_COLS:
            pre_ohe[col] = imputed_df[f"{col}_enc"].values

        # OHE sin drop_first
        df_ohe = pd.get_dummies(pre_ohe, columns=self.CATEGORICAL_COLS, drop_first=False)
        # Eliminar columnas _0 (equivalente a drop_first=True del entrenamiento)
        for col in self.CATEGORICAL_COLS:
            if f"{col}_0" in df_ohe.columns:
                df_ohe = df_ohe.drop(columns=[f"{col}_0"])

        # Alinear con columnas del entrenamiento
        df_ohe = df_ohe.reindex(columns=self.feature_columns, fill_value=0)

        # Paso 4: Escalar numéricas
        df_ohe[self.NUMERIC_COLS] = self.scaler.transform(df_ohe[self.NUMERIC_COLS])

        return df_ohe

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
