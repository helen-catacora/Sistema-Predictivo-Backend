-- ===================================================
-- Esquema revisado - Sistema Predictivo
-- Ejecutar en PostgreSQL 17 (BD: sistema_predictivo_bd)
-- ===================================================

-- 1. GESTIÓN DE SEGURIDAD Y ACCESO (RBAC)
-- ===================================================
CREATE TABLE IF NOT EXISTS roles (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS usuarios (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre text NOT NULL,
    email text NOT NULL UNIQUE,
    password_hash text,
    rol_id bigint NOT NULL REFERENCES roles(id),
    estado text NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'inactivo')),
    carnet_identidad text,
    telefono text,
    cargo text
);

CREATE TABLE IF NOT EXISTS modulos (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS usuario_modulo (
    usuario_id bigint NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    modulo_id bigint NOT NULL REFERENCES modulos(id) ON DELETE CASCADE,
    PRIMARY KEY (usuario_id, modulo_id)
);

-- 2. ESTRUCTURA ACADÉMICA INSTITUCIONAL
-- ===================================================
CREATE TABLE IF NOT EXISTS semestres (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS areas (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS paralelos (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre text NOT NULL,
    area_id bigint NOT NULL REFERENCES areas(id),
    semestre_id bigint REFERENCES semestres(id),
    encargado_id bigint NOT NULL REFERENCES usuarios(id),
    UNIQUE(nombre, area_id)
);

-- 3. ENTIDADES ESTUDIANTILES Y MATERIAS
-- ===================================================
CREATE TABLE IF NOT EXISTS estudiantes (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    codigo_estudiante text NOT NULL UNIQUE,
    nombre text NOT NULL,
    apellido text NOT NULL,
    paralelo_id bigint NOT NULL REFERENCES paralelos(id)
);

CREATE TABLE IF NOT EXISTS materias (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre text NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS malla_curricular (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    materia_id bigint REFERENCES materias(id),
    area_id bigint REFERENCES areas(id),
    semestre_id bigint REFERENCES semestres(id),
    UNIQUE(materia_id, area_id, semestre_id)
);

-- 4. PROCESAMIENTO DE LA MATRIZ DE INSCRIPCIÓN (EXCEL)
-- ===================================================
CREATE TABLE IF NOT EXISTS inscripciones (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    estudiante_id bigint NOT NULL REFERENCES estudiantes(id),
    materia_id bigint NOT NULL REFERENCES materias(id),
    gestion_academica text NOT NULL,
    UNIQUE(estudiante_id, materia_id, gestion_academica)
);

-- 5. REGISTRO OPERATIVO Y PREDICCIÓN
-- ===================================================
CREATE TABLE IF NOT EXISTS asistencias (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    fecha date NOT NULL,
    estado text NOT NULL CHECK (estado IN ('Presente', 'Ausente', 'Justificado', 'No Cursa')),
    observacion text,
    estudiante_id bigint NOT NULL REFERENCES estudiantes(id),
    materia_id bigint NOT NULL REFERENCES materias(id),
    encargado_id bigint NOT NULL REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS predicciones (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    probabilidad_abandono double precision NOT NULL,
    nivel_riesgo text NOT NULL CHECK (nivel_riesgo IN ('Bajo', 'Medio', 'Alto', 'Critico')),
    fecha_prediccion date NOT NULL,
    estudiante_id bigint NOT NULL REFERENCES estudiantes(id)
);

CREATE TABLE IF NOT EXISTS acciones (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    descripcion text NOT NULL,
    fecha date NOT NULL,
    prediccion_id bigint NOT NULL REFERENCES predicciones(id)
);

-- Índices opcionales para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_inscripciones_estudiante_gestion ON inscripciones(estudiante_id, gestion_academica);
CREATE INDEX IF NOT EXISTS idx_asistencias_estudiante_materia_fecha ON asistencias(estudiante_id, materia_id, fecha);
CREATE INDEX IF NOT EXISTS idx_predicciones_estudiante_fecha ON predicciones(estudiante_id, fecha_prediccion DESC);
