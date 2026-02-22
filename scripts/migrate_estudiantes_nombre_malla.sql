-- Migración: agrega columna nombre_malla a estudiantes
-- Relaciona al estudiante con su plan curricular (malla_curricular.nombre_malla)

ALTER TABLE estudiantes
    ADD COLUMN IF NOT EXISTS nombre_malla TEXT;
