-- Migración: restricción por usuario (tabla usuario_modulo)
-- Ejecutar en la BD existente. La restricción pasa de rol a usuario: cada usuario tiene sus propios módulos.

-- 1. Crear tabla usuario_modulo (usuario_id, modulo_id)
CREATE TABLE IF NOT EXISTS usuario_modulo (
    usuario_id bigint NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    modulo_id bigint NOT NULL REFERENCES modulos(id) ON DELETE CASCADE,
    PRIMARY KEY (usuario_id, modulo_id)
);

-- 2. Asignar todos los módulos a todos los usuarios (mantienen acceso hasta que los restrinjas)
INSERT INTO usuario_modulo (usuario_id, modulo_id)
SELECT u.id, m.id
FROM usuarios u
CROSS JOIN modulos m
ON CONFLICT (usuario_id, modulo_id) DO NOTHING;
