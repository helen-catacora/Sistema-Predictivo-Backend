-- Migración: agrega columna nombre_malla a malla_curricular
-- Poblar registros existentes con "Competencias 2024-2028"

ALTER TABLE malla_curricular
    ADD COLUMN IF NOT EXISTS nombre_malla TEXT;

UPDATE malla_curricular
SET nombre_malla = 'Competencias 2024-2028'
WHERE nombre_malla IS NULL;
