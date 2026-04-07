-- Migración: Renombrar módulo + crear tabla entrenamientos_modelo
-- Ejecutar con: psql -h 127.0.0.1 -U postgres -d sistema_predictivo_bd -f scripts/migrate_entrenamiento_modelo.sql

-- 1. Renombrar módulo
UPDATE modulos SET nombre = 'Predicciones' WHERE nombre = 'Visualización de Predicciones';

-- 2. Tabla de historial de entrenamientos del modelo ML
CREATE TABLE IF NOT EXISTS entrenamientos_modelo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha_inicio TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_fin TIMESTAMPTZ,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    nombre_archivo TEXT NOT NULL,
    total_registros INTEGER NOT NULL DEFAULT 0,
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id),
    version_generada TEXT,
    metricas_nuevo JSONB,
    metricas_actual JSONB,
    parametros_modelo JSONB,
    tipo_mejor_modelo TEXT,
    ruta_artefactos_candidatos TEXT,
    mensaje_error TEXT,
    aceptado_por_usuario_id BIGINT REFERENCES usuarios(id),
    fecha_decision TIMESTAMPTZ
);
