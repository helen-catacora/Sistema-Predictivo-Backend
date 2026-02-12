--
-- PostgreSQL database dump
--

\restrict Fxi5qfg9fqmgoCtMXdgKNtnpCQrpsJndFDbyXqlY5g4rq5KxoN7nUZZrAqgfstu

-- Dumped from database version 17.7
-- Dumped by pg_dump version 17.7

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: acciones; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.acciones (
    id bigint NOT NULL,
    descripcion text NOT NULL,
    fecha date NOT NULL,
    prediccion_id bigint NOT NULL
);


ALTER TABLE public.acciones OWNER TO postgres;

--
-- Name: acciones_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.acciones ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.acciones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: alertas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alertas (
    id bigint NOT NULL,
    tipo text NOT NULL,
    nivel text NOT NULL,
    estudiante_id bigint NOT NULL,
    prediccion_id bigint,
    titulo text NOT NULL,
    descripcion text NOT NULL,
    fecha_creacion timestamp with time zone DEFAULT now() NOT NULL,
    fecha_resolucion timestamp with time zone,
    estado text DEFAULT 'activa'::text NOT NULL,
    resuelta_por_id bigint,
    observacion_resolucion text,
    faltas_consecutivas integer DEFAULT 0 NOT NULL,
    gestion_id bigint,
    CONSTRAINT alertas_estado_check CHECK ((estado = ANY (ARRAY['activa'::text, 'en_seguimiento'::text, 'resuelta'::text, 'descartada'::text]))),
    CONSTRAINT alertas_nivel_check CHECK ((nivel = ANY (ARRAY['Bajo'::text, 'Medio'::text, 'Alto'::text, 'Critico'::text]))),
    CONSTRAINT alertas_tipo_check CHECK ((tipo = ANY (ARRAY['temprana'::text, 'critica'::text, 'abandono'::text])))
);


ALTER TABLE public.alertas OWNER TO postgres;

--
-- Name: alertas_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.alertas ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.alertas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: areas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.areas (
    id bigint NOT NULL,
    nombre text NOT NULL
);


ALTER TABLE public.areas OWNER TO postgres;

--
-- Name: areas_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.areas ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.areas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: asistencias; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.asistencias (
    id bigint NOT NULL,
    fecha date NOT NULL,
    estado text NOT NULL,
    observacion text,
    estudiante_id bigint NOT NULL,
    materia_id bigint NOT NULL,
    encargado_id bigint NOT NULL
);


ALTER TABLE public.asistencias OWNER TO postgres;

--
-- Name: asistencias_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.asistencias ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.asistencias_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: estudiantes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.estudiantes (
    id bigint NOT NULL,
    codigo_estudiante text NOT NULL,
    nombre text NOT NULL,
    apellido text NOT NULL,
    paralelo_id bigint NOT NULL,
    fecha_nacimiento date,
    genero text,
    grado text,
    estrato_socioeconomico text,
    ocupacion_laboral text,
    con_quien_vive text,
    apoyo_economico text,
    modalidad_ingreso text,
    tipo_colegio text,
    CONSTRAINT estudiantes_apoyo_economico_check CHECK ((apoyo_economico = ANY (ARRAY['Ninguno'::text, 'Parcial'::text, 'Total'::text]))),
    CONSTRAINT estudiantes_con_quien_vive_check CHECK ((con_quien_vive = ANY (ARRAY['Con Familiares'::text, 'Con mi novia'::text, 'Con mis padres'::text, 'En residencia o alojamiento estudiantil'::text, 'Solo/a'::text]))),
    CONSTRAINT estudiantes_estrato_socioeconomico_check CHECK ((estrato_socioeconomico = ANY (ARRAY['Alto'::text, 'Bajo'::text, 'Medio'::text]))),
    CONSTRAINT estudiantes_genero_check CHECK ((genero = ANY (ARRAY['Masculino'::text, 'Femenino'::text]))),
    CONSTRAINT estudiantes_grado_check CHECK ((grado = ANY (ARRAY['Civil'::text, 'Militar'::text]))),
    CONSTRAINT estudiantes_modalidad_ingreso_check CHECK ((modalidad_ingreso = ANY (ARRAY['Admision Especial'::text, 'Curso Preuniversitario/Intensivo'::text, 'Curso Vestibular'::text, 'Prueba de Suficiencia Academica'::text]))),
    CONSTRAINT estudiantes_ocupacion_laboral_check CHECK ((ocupacion_laboral = ANY (ARRAY['Si'::text, 'No'::text]))),
    CONSTRAINT estudiantes_tipo_colegio_check CHECK ((tipo_colegio = ANY (ARRAY['Convenio'::text, 'Privado'::text, 'Publico'::text])))
);


ALTER TABLE public.estudiantes OWNER TO postgres;

--
-- Name: estudiantes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.estudiantes ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.estudiantes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: gestiones_academicas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gestiones_academicas (
    id bigint NOT NULL,
    nombre text NOT NULL,
    fecha_inicio date NOT NULL,
    fecha_fin date NOT NULL,
    activa boolean DEFAULT false NOT NULL
);


ALTER TABLE public.gestiones_academicas OWNER TO postgres;

--
-- Name: gestiones_academicas_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.gestiones_academicas ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.gestiones_academicas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: inscripciones; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inscripciones (
    id bigint NOT NULL,
    estudiante_id bigint NOT NULL,
    materia_id bigint NOT NULL,
    gestion_academica text NOT NULL,
    gestion_id bigint
);


ALTER TABLE public.inscripciones OWNER TO postgres;

--
-- Name: inscripciones_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.inscripciones ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.inscripciones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lotes_prediccion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lotes_prediccion (
    id bigint NOT NULL,
    nombre_archivo text NOT NULL,
    fecha_carga timestamp with time zone DEFAULT now() NOT NULL,
    usuario_id bigint NOT NULL,
    gestion_id bigint,
    estado text DEFAULT 'pendiente'::text NOT NULL,
    total_estudiantes integer DEFAULT 0 NOT NULL,
    total_procesados integer DEFAULT 0 NOT NULL,
    total_alto_riesgo integer DEFAULT 0 NOT NULL,
    total_medio_riesgo integer DEFAULT 0 NOT NULL,
    total_bajo_riesgo integer DEFAULT 0 NOT NULL,
    total_critico integer DEFAULT 0 NOT NULL,
    mensaje_error text,
    version_modelo text DEFAULT 'v2_con_imputacion_knn'::text NOT NULL,
    CONSTRAINT lotes_prediccion_estado_check CHECK ((estado = ANY (ARRAY['pendiente'::text, 'procesando'::text, 'completado'::text, 'error'::text])))
);


ALTER TABLE public.lotes_prediccion OWNER TO postgres;

--
-- Name: lotes_prediccion_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.lotes_prediccion ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lotes_prediccion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: malla_curricular; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.malla_curricular (
    id bigint NOT NULL,
    materia_id bigint,
    area_id bigint,
    semestre_id bigint
);


ALTER TABLE public.malla_curricular OWNER TO postgres;

--
-- Name: malla_curricular_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.malla_curricular ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.malla_curricular_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: materias; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.materias (
    id bigint NOT NULL,
    nombre text NOT NULL
);


ALTER TABLE public.materias OWNER TO postgres;

--
-- Name: materias_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.materias ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.materias_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: modulos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.modulos (
    id bigint NOT NULL,
    nombre text NOT NULL
);


ALTER TABLE public.modulos OWNER TO postgres;

--
-- Name: modulos_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.modulos ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.modulos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: paralelos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paralelos (
    id bigint NOT NULL,
    nombre text NOT NULL,
    area_id bigint NOT NULL,
    encargado_id bigint NOT NULL,
    semestre_id bigint
);


ALTER TABLE public.paralelos OWNER TO postgres;

--
-- Name: paralelos_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.paralelos ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.paralelos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: predicciones; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.predicciones (
    id bigint NOT NULL,
    probabilidad_abandono double precision NOT NULL,
    nivel_riesgo text NOT NULL,
    fecha_prediccion date NOT NULL,
    estudiante_id bigint NOT NULL,
    lote_id bigint,
    gestion_id bigint,
    tipo text DEFAULT 'masiva'::text NOT NULL,
    features_utilizadas jsonb,
    version_modelo text,
    CONSTRAINT predicciones_tipo_check CHECK ((tipo = ANY (ARRAY['individual'::text, 'masiva'::text])))
);


ALTER TABLE public.predicciones OWNER TO postgres;

--
-- Name: predicciones_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.predicciones ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.predicciones_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: reportes_generados; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reportes_generados (
    id bigint NOT NULL,
    tipo text NOT NULL,
    nombre text NOT NULL,
    generado_por_id bigint NOT NULL,
    fecha_generacion timestamp with time zone NOT NULL,
    parametros jsonb
);


ALTER TABLE public.reportes_generados OWNER TO postgres;

--
-- Name: reportes_generados_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.reportes_generados ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.reportes_generados_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    id bigint NOT NULL,
    nombre text NOT NULL
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.roles ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.roles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: semestres; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.semestres (
    id bigint NOT NULL,
    nombre text NOT NULL
);


ALTER TABLE public.semestres OWNER TO postgres;

--
-- Name: semestres_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.semestres ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.semestres_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: usuario_modulo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usuario_modulo (
    usuario_id bigint NOT NULL,
    modulo_id bigint NOT NULL
);


ALTER TABLE public.usuario_modulo OWNER TO postgres;

--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usuarios (
    id bigint NOT NULL,
    nombre text NOT NULL,
    email text NOT NULL,
    password_hash text,
    rol_id bigint NOT NULL,
    estado text DEFAULT 'activo'::text NOT NULL,
    cargo text,
    carnet_identidad text,
    telefono text,
    CONSTRAINT usuarios_estado_check CHECK ((estado = ANY (ARRAY['activo'::text, 'inactivo'::text])))
);


ALTER TABLE public.usuarios OWNER TO postgres;

--
-- Name: usuarios_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.usuarios ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.usuarios_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: acciones acciones_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.acciones
    ADD CONSTRAINT acciones_pkey PRIMARY KEY (id);


--
-- Name: alertas alertas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alertas
    ADD CONSTRAINT alertas_pkey PRIMARY KEY (id);


--
-- Name: areas areas_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.areas
    ADD CONSTRAINT areas_nombre_key UNIQUE (nombre);


--
-- Name: areas areas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.areas
    ADD CONSTRAINT areas_pkey PRIMARY KEY (id);


--
-- Name: asistencias asistencias_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asistencias
    ADD CONSTRAINT asistencias_pkey PRIMARY KEY (id);


--
-- Name: estudiantes estudiantes_codigo_estudiante_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.estudiantes
    ADD CONSTRAINT estudiantes_codigo_estudiante_key UNIQUE (codigo_estudiante);


--
-- Name: estudiantes estudiantes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.estudiantes
    ADD CONSTRAINT estudiantes_pkey PRIMARY KEY (id);


--
-- Name: gestiones_academicas gestiones_academicas_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gestiones_academicas
    ADD CONSTRAINT gestiones_academicas_nombre_key UNIQUE (nombre);


--
-- Name: gestiones_academicas gestiones_academicas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gestiones_academicas
    ADD CONSTRAINT gestiones_academicas_pkey PRIMARY KEY (id);


--
-- Name: inscripciones inscripciones_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inscripciones
    ADD CONSTRAINT inscripciones_pkey PRIMARY KEY (id);


--
-- Name: lotes_prediccion lotes_prediccion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lotes_prediccion
    ADD CONSTRAINT lotes_prediccion_pkey PRIMARY KEY (id);


--
-- Name: malla_curricular malla_curricular_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.malla_curricular
    ADD CONSTRAINT malla_curricular_pkey PRIMARY KEY (id);


--
-- Name: materias materias_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.materias
    ADD CONSTRAINT materias_nombre_key UNIQUE (nombre);


--
-- Name: materias materias_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.materias
    ADD CONSTRAINT materias_pkey PRIMARY KEY (id);


--
-- Name: modulos modulos_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modulos
    ADD CONSTRAINT modulos_nombre_key UNIQUE (nombre);


--
-- Name: modulos modulos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modulos
    ADD CONSTRAINT modulos_pkey PRIMARY KEY (id);


--
-- Name: paralelos paralelos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paralelos
    ADD CONSTRAINT paralelos_pkey PRIMARY KEY (id);


--
-- Name: predicciones predicciones_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.predicciones
    ADD CONSTRAINT predicciones_pkey PRIMARY KEY (id);


--
-- Name: reportes_generados reportes_generados_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reportes_generados
    ADD CONSTRAINT reportes_generados_pkey PRIMARY KEY (id);


--
-- Name: roles roles_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_nombre_key UNIQUE (nombre);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: semestres semestres_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semestres
    ADD CONSTRAINT semestres_nombre_key UNIQUE (nombre);


--
-- Name: semestres semestres_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.semestres
    ADD CONSTRAINT semestres_pkey PRIMARY KEY (id);


--
-- Name: inscripciones uq_inscripciones_estudiante_materia_gestion; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inscripciones
    ADD CONSTRAINT uq_inscripciones_estudiante_materia_gestion UNIQUE (estudiante_id, materia_id, gestion_academica);


--
-- Name: malla_curricular uq_malla_curricular_materia_area_semestre; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.malla_curricular
    ADD CONSTRAINT uq_malla_curricular_materia_area_semestre UNIQUE (materia_id, area_id, semestre_id);


--
-- Name: paralelos uq_paralelos_nombre_area_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paralelos
    ADD CONSTRAINT uq_paralelos_nombre_area_id UNIQUE (nombre, area_id);


--
-- Name: usuario_modulo usuario_modulo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario_modulo
    ADD CONSTRAINT usuario_modulo_pkey PRIMARY KEY (usuario_id, modulo_id);


--
-- Name: usuarios usuarios_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_email_key UNIQUE (email);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: ix_alertas_estado; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alertas_estado ON public.alertas USING btree (estado);


--
-- Name: ix_alertas_estudiante; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alertas_estudiante ON public.alertas USING btree (estudiante_id);


--
-- Name: ix_alertas_fecha; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alertas_fecha ON public.alertas USING btree (fecha_creacion DESC);


--
-- Name: ix_alertas_gestion; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alertas_gestion ON public.alertas USING btree (gestion_id);


--
-- Name: ix_alertas_tipo; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_alertas_tipo ON public.alertas USING btree (tipo);


--
-- Name: ix_lotes_prediccion_fecha; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_lotes_prediccion_fecha ON public.lotes_prediccion USING btree (fecha_carga DESC);


--
-- Name: ix_lotes_prediccion_usuario; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_lotes_prediccion_usuario ON public.lotes_prediccion USING btree (usuario_id);


--
-- Name: ix_predicciones_gestion; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_predicciones_gestion ON public.predicciones USING btree (gestion_id);


--
-- Name: ix_predicciones_lote; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_predicciones_lote ON public.predicciones USING btree (lote_id);


--
-- Name: ix_predicciones_tipo; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_predicciones_tipo ON public.predicciones USING btree (tipo);


--
-- Name: uq_gestiones_academicas_activa; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_gestiones_academicas_activa ON public.gestiones_academicas USING btree (activa) WHERE (activa = true);


--
-- Name: acciones acciones_prediccion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.acciones
    ADD CONSTRAINT acciones_prediccion_id_fkey FOREIGN KEY (prediccion_id) REFERENCES public.predicciones(id);


--
-- Name: alertas alertas_estudiante_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alertas
    ADD CONSTRAINT alertas_estudiante_id_fkey FOREIGN KEY (estudiante_id) REFERENCES public.estudiantes(id);


--
-- Name: alertas alertas_gestion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alertas
    ADD CONSTRAINT alertas_gestion_id_fkey FOREIGN KEY (gestion_id) REFERENCES public.gestiones_academicas(id);


--
-- Name: alertas alertas_prediccion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alertas
    ADD CONSTRAINT alertas_prediccion_id_fkey FOREIGN KEY (prediccion_id) REFERENCES public.predicciones(id);


--
-- Name: alertas alertas_resuelta_por_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alertas
    ADD CONSTRAINT alertas_resuelta_por_id_fkey FOREIGN KEY (resuelta_por_id) REFERENCES public.usuarios(id);


--
-- Name: asistencias asistencias_encargado_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asistencias
    ADD CONSTRAINT asistencias_encargado_id_fkey FOREIGN KEY (encargado_id) REFERENCES public.usuarios(id);


--
-- Name: asistencias asistencias_estudiante_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asistencias
    ADD CONSTRAINT asistencias_estudiante_id_fkey FOREIGN KEY (estudiante_id) REFERENCES public.estudiantes(id);


--
-- Name: asistencias asistencias_materia_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.asistencias
    ADD CONSTRAINT asistencias_materia_id_fkey FOREIGN KEY (materia_id) REFERENCES public.materias(id);


--
-- Name: estudiantes estudiantes_paralelo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.estudiantes
    ADD CONSTRAINT estudiantes_paralelo_id_fkey FOREIGN KEY (paralelo_id) REFERENCES public.paralelos(id);


--
-- Name: inscripciones inscripciones_estudiante_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inscripciones
    ADD CONSTRAINT inscripciones_estudiante_id_fkey FOREIGN KEY (estudiante_id) REFERENCES public.estudiantes(id);


--
-- Name: inscripciones inscripciones_gestion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inscripciones
    ADD CONSTRAINT inscripciones_gestion_id_fkey FOREIGN KEY (gestion_id) REFERENCES public.gestiones_academicas(id);


--
-- Name: inscripciones inscripciones_materia_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inscripciones
    ADD CONSTRAINT inscripciones_materia_id_fkey FOREIGN KEY (materia_id) REFERENCES public.materias(id);


--
-- Name: lotes_prediccion lotes_prediccion_gestion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lotes_prediccion
    ADD CONSTRAINT lotes_prediccion_gestion_id_fkey FOREIGN KEY (gestion_id) REFERENCES public.gestiones_academicas(id);


--
-- Name: lotes_prediccion lotes_prediccion_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lotes_prediccion
    ADD CONSTRAINT lotes_prediccion_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);


--
-- Name: malla_curricular malla_curricular_area_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.malla_curricular
    ADD CONSTRAINT malla_curricular_area_id_fkey FOREIGN KEY (area_id) REFERENCES public.areas(id);


--
-- Name: malla_curricular malla_curricular_materia_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.malla_curricular
    ADD CONSTRAINT malla_curricular_materia_id_fkey FOREIGN KEY (materia_id) REFERENCES public.materias(id);


--
-- Name: malla_curricular malla_curricular_semestre_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.malla_curricular
    ADD CONSTRAINT malla_curricular_semestre_id_fkey FOREIGN KEY (semestre_id) REFERENCES public.semestres(id);


--
-- Name: paralelos paralelos_area_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paralelos
    ADD CONSTRAINT paralelos_area_id_fkey FOREIGN KEY (area_id) REFERENCES public.areas(id);


--
-- Name: paralelos paralelos_encargado_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paralelos
    ADD CONSTRAINT paralelos_encargado_id_fkey FOREIGN KEY (encargado_id) REFERENCES public.usuarios(id);


--
-- Name: paralelos paralelos_semestre_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paralelos
    ADD CONSTRAINT paralelos_semestre_id_fkey FOREIGN KEY (semestre_id) REFERENCES public.semestres(id);


--
-- Name: predicciones predicciones_estudiante_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.predicciones
    ADD CONSTRAINT predicciones_estudiante_id_fkey FOREIGN KEY (estudiante_id) REFERENCES public.estudiantes(id);


--
-- Name: predicciones predicciones_gestion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.predicciones
    ADD CONSTRAINT predicciones_gestion_id_fkey FOREIGN KEY (gestion_id) REFERENCES public.gestiones_academicas(id);


--
-- Name: predicciones predicciones_lote_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.predicciones
    ADD CONSTRAINT predicciones_lote_id_fkey FOREIGN KEY (lote_id) REFERENCES public.lotes_prediccion(id);


--
-- Name: reportes_generados reportes_generados_generado_por_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reportes_generados
    ADD CONSTRAINT reportes_generados_generado_por_id_fkey FOREIGN KEY (generado_por_id) REFERENCES public.usuarios(id);


--
-- Name: usuario_modulo usuario_modulo_modulo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario_modulo
    ADD CONSTRAINT usuario_modulo_modulo_id_fkey FOREIGN KEY (modulo_id) REFERENCES public.modulos(id) ON DELETE CASCADE;


--
-- Name: usuario_modulo usuario_modulo_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuario_modulo
    ADD CONSTRAINT usuario_modulo_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id) ON DELETE CASCADE;


--
-- Name: usuarios usuarios_rol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_rol_id_fkey FOREIGN KEY (rol_id) REFERENCES public.roles(id);


--
-- PostgreSQL database dump complete
--

\unrestrict Fxi5qfg9fqmgoCtMXdgKNtnpCQrpsJndFDbyXqlY5g4rq5KxoN7nUZZrAqgfstu

