-- Migración: Agregar campo motivo_inactivacion a usuarios
-- Fecha: 2026-03-11

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS motivo_inactivacion TEXT;
