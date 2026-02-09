-- ============================================================
-- MIGRACIÓN: Corregir CHECK constraints de estudiantes
-- Fecha: 2026-02-07
-- Descripción: Los CHECK constraints originales no coincidían
--   con las categorías reales del label_encoders.pkl del modelo ML.
-- ============================================================

BEGIN;

-- 1. estrato_socioeconomico: cambiar de INTEGER a TEXT
ALTER TABLE estudiantes DROP CONSTRAINT IF EXISTS estudiantes_estrato_socioeconomico_check;
ALTER TABLE estudiantes ALTER COLUMN estrato_socioeconomico TYPE TEXT USING estrato_socioeconomico::TEXT;
ALTER TABLE estudiantes ADD CONSTRAINT estudiantes_estrato_socioeconomico_check
    CHECK (estrato_socioeconomico IN ('Alto', 'Bajo', 'Medio'));

-- 2. con_quien_vive: actualizar categorías
ALTER TABLE estudiantes DROP CONSTRAINT IF EXISTS estudiantes_con_quien_vive_check;
ALTER TABLE estudiantes ADD CONSTRAINT estudiantes_con_quien_vive_check
    CHECK (con_quien_vive IN (
        'Con Familiares', 'Con mi novia', 'Con mis padres',
        'En residencia o alojamiento estudiantil', 'Solo/a'
    ));

-- 3. apoyo_economico: actualizar categorías
ALTER TABLE estudiantes DROP CONSTRAINT IF EXISTS estudiantes_apoyo_economico_check;
ALTER TABLE estudiantes ADD CONSTRAINT estudiantes_apoyo_economico_check
    CHECK (apoyo_economico IN ('Ninguno', 'Parcial', 'Total'));

-- 4. modalidad_ingreso: actualizar categorías
ALTER TABLE estudiantes DROP CONSTRAINT IF EXISTS estudiantes_modalidad_ingreso_check;
ALTER TABLE estudiantes ADD CONSTRAINT estudiantes_modalidad_ingreso_check
    CHECK (modalidad_ingreso IN (
        'Admision Especial', 'Curso Preuniversitario/Intensivo',
        'Curso Vestibular', 'Prueba de Suficiencia Academica'
    ));

-- 5. tipo_colegio: agregar 'Convenio'
ALTER TABLE estudiantes DROP CONSTRAINT IF EXISTS estudiantes_tipo_colegio_check;
ALTER TABLE estudiantes ADD CONSTRAINT estudiantes_tipo_colegio_check
    CHECK (tipo_colegio IN ('Convenio', 'Privado', 'Publico'));

COMMIT;
