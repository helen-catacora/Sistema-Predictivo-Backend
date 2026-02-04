-- Migración: columna estado en usuarios + tabla modulos (restricción por usuario con usuario_modulo).
-- Ejecutar en la BD existente (PostgreSQL). Para instalación nueva use schema.sql.

-- 1. Columna estado en usuarios (activo/inactivo)
ALTER TABLE usuarios
ADD COLUMN IF NOT EXISTS estado text NOT NULL DEFAULT 'activo';

ALTER TABLE usuarios
DROP CONSTRAINT IF EXISTS usuarios_estado_check;

ALTER TABLE usuarios
ADD CONSTRAINT usuarios_estado_check CHECK (estado IN ('activo', 'inactivo'));

-- 2. Tabla de módulos
CREATE TABLE IF NOT EXISTS modulos (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre text NOT NULL UNIQUE
);

-- 3. Insertar módulos por defecto
INSERT INTO modulos (nombre) VALUES
    ('asistencias'),
    ('estudiantes'),
    ('reportes'),
    ('configuracion')
ON CONFLICT (nombre) DO NOTHING;
