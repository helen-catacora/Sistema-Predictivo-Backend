-- Añade semestre_id a la tabla paralelos.
ALTER TABLE paralelos ADD COLUMN IF NOT EXISTS semestre_id bigint REFERENCES semestres(id);
