-- ============================================================
-- MIGRACIÓN: Predicciones, Alertas, Gestiones Académicas
-- Fecha: 2026-02-07
-- Descripción: Agrega tablas y columnas necesarias para el
--   sistema de predicción ML, alertas de abandono y gestiones.
-- ============================================================

BEGIN;

-- 1. Tabla gestiones_academicas (NUEVA)
CREATE TABLE IF NOT EXISTS gestiones_academicas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT false
);

-- Solo una gestión activa a la vez
CREATE UNIQUE INDEX IF NOT EXISTS uq_gestiones_academicas_activa
    ON gestiones_academicas (activa) WHERE activa = true;

-- 2. Columnas sociodemográficas en estudiantes
ALTER TABLE estudiantes ADD COLUMN IF NOT EXISTS fecha_nacimiento DATE;
ALTER TABLE estudiantes ADD COLUMN IF NOT EXISTS genero TEXT
    CHECK (genero IN ('Masculino', 'Femenino'));
ALTER TABLE estudiantes ADD COLUMN IF NOT EXISTS grado TEXT
    CHECK (grado IN ('Civil', 'Militar'));
ALTER TABLE estudiantes ADD COLUMN IF NOT EXISTS estrato_socioeconomico INTEGER
    CHECK (estrato_socioeconomico BETWEEN 1 AND 6);
ALTER TABLE estudiantes ADD COLUMN IF NOT EXISTS ocupacion_laboral TEXT
    CHECK (ocupacion_laboral IN ('Si', 'No'));
ALTER TABLE estudiantes ADD COLUMN IF NOT EXISTS con_quien_vive TEXT
    CHECK (con_quien_vive IN ('Familia', 'Solo', 'Otro'));
ALTER TABLE estudiantes ADD COLUMN IF NOT EXISTS apoyo_economico TEXT
    CHECK (apoyo_economico IN ('Beca', 'Credito', 'Otro', 'Ninguno'));
ALTER TABLE estudiantes ADD COLUMN IF NOT EXISTS modalidad_ingreso TEXT
    CHECK (modalidad_ingreso IN ('Admision Especial', 'Prueba Suficiencia Academica', 'Admision Regular'));
ALTER TABLE estudiantes ADD COLUMN IF NOT EXISTS tipo_colegio TEXT
    CHECK (tipo_colegio IN ('Publico', 'Privado'));

-- 3. FK gestion_id en inscripciones (migración gradual)
ALTER TABLE inscripciones ADD COLUMN IF NOT EXISTS gestion_id BIGINT
    REFERENCES gestiones_academicas(id);

-- 4. Tabla lotes_prediccion (NUEVA)
CREATE TABLE IF NOT EXISTS lotes_prediccion (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_archivo TEXT NOT NULL,
    fecha_carga TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id),
    gestion_id BIGINT REFERENCES gestiones_academicas(id),
    estado TEXT NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'procesando', 'completado', 'error')),
    total_estudiantes INTEGER NOT NULL DEFAULT 0,
    total_procesados INTEGER NOT NULL DEFAULT 0,
    total_alto_riesgo INTEGER NOT NULL DEFAULT 0,
    total_medio_riesgo INTEGER NOT NULL DEFAULT 0,
    total_bajo_riesgo INTEGER NOT NULL DEFAULT 0,
    total_critico INTEGER NOT NULL DEFAULT 0,
    mensaje_error TEXT,
    version_modelo TEXT NOT NULL DEFAULT 'v2_con_imputacion_knn'
);

CREATE INDEX IF NOT EXISTS ix_lotes_prediccion_fecha
    ON lotes_prediccion (fecha_carga DESC);
CREATE INDEX IF NOT EXISTS ix_lotes_prediccion_usuario
    ON lotes_prediccion (usuario_id);

-- 5. Nuevas columnas en predicciones
ALTER TABLE predicciones ADD COLUMN IF NOT EXISTS lote_id BIGINT
    REFERENCES lotes_prediccion(id);
ALTER TABLE predicciones ADD COLUMN IF NOT EXISTS gestion_id BIGINT
    REFERENCES gestiones_academicas(id);
ALTER TABLE predicciones ADD COLUMN IF NOT EXISTS tipo TEXT NOT NULL DEFAULT 'masiva'
    CHECK (tipo IN ('individual', 'masiva'));
ALTER TABLE predicciones ADD COLUMN IF NOT EXISTS features_utilizadas JSONB;
ALTER TABLE predicciones ADD COLUMN IF NOT EXISTS version_modelo TEXT;

CREATE INDEX IF NOT EXISTS ix_predicciones_lote ON predicciones (lote_id);
CREATE INDEX IF NOT EXISTS ix_predicciones_gestion ON predicciones (gestion_id);
CREATE INDEX IF NOT EXISTS ix_predicciones_tipo ON predicciones (tipo);

-- 6. Tabla alertas (NUEVA)
CREATE TABLE IF NOT EXISTS alertas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo TEXT NOT NULL CHECK (tipo IN ('temprana', 'critica', 'abandono')),
    nivel TEXT NOT NULL CHECK (nivel IN ('Bajo', 'Medio', 'Alto', 'Critico')),
    estudiante_id BIGINT NOT NULL REFERENCES estudiantes(id),
    prediccion_id BIGINT REFERENCES predicciones(id),
    titulo TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_creacion TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    fecha_resolucion TIMESTAMP WITH TIME ZONE,
    estado TEXT NOT NULL DEFAULT 'activa'
        CHECK (estado IN ('activa', 'en_seguimiento', 'resuelta', 'descartada')),
    resuelta_por_id BIGINT REFERENCES usuarios(id),
    observacion_resolucion TEXT,
    faltas_consecutivas INTEGER NOT NULL DEFAULT 0,
    gestion_id BIGINT REFERENCES gestiones_academicas(id)
);

CREATE INDEX IF NOT EXISTS ix_alertas_estudiante ON alertas (estudiante_id);
CREATE INDEX IF NOT EXISTS ix_alertas_estado ON alertas (estado);
CREATE INDEX IF NOT EXISTS ix_alertas_tipo ON alertas (tipo);
CREATE INDEX IF NOT EXISTS ix_alertas_fecha ON alertas (fecha_creacion DESC);
CREATE INDEX IF NOT EXISTS ix_alertas_gestion ON alertas (gestion_id);

-- 7. Nuevo módulo de predicciones para control de acceso
INSERT INTO modulos (nombre) VALUES ('predicciones') ON CONFLICT (nombre) DO NOTHING;

COMMIT;
