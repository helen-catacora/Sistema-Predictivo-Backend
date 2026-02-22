-- Migración: reemplaza la constraint única de malla_curricular
-- La nueva clave de unicidad incluye nombre_malla para permitir
-- la misma combinación materia+área+semestre bajo diferentes mallas.

ALTER TABLE malla_curricular
    DROP CONSTRAINT IF EXISTS uq_malla_curricular_materia_area_semestre;

ALTER TABLE malla_curricular
    ADD CONSTRAINT uq_malla_curricular_materia_area_semestre_nombre
    UNIQUE (materia_id, area_id, semestre_id, nombre_malla);
