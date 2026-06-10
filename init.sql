--
-- Minimal PostgreSQL schema
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';
SET default_table_access_method = heap;

CREATE SEQUENCE public.expenses_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.expenses (
    id bigint DEFAULT nextval('public.expenses_id_seq'::regclass) NOT NULL,
    concept text NOT NULL,
    date date NOT NULL,
    amount numeric(12,2) NOT NULL,
    user_name text NOT NULL,
    attachment_type text,
    attachment_file_id text,
    attachment_name text
);

ALTER SEQUENCE public.expenses_id_seq OWNED BY public.expenses.id;

CREATE SEQUENCE public.trips_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.trips (
    id bigint DEFAULT nextval('public.trips_id_seq'::regclass) NOT NULL,
    date date NOT NULL,
    user_name text NOT NULL
);

ALTER SEQUENCE public.trips_id_seq OWNED BY public.trips.id;

CREATE SEQUENCE public.fuel_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE public.fuel (
    id bigint DEFAULT nextval('public.fuel_id_seq'::regclass) NOT NULL,
    date date NOT NULL,
    price numeric(12,3) NOT NULL,
    user_name text NOT NULL
);

ALTER SEQUENCE public.fuel_id_seq OWNED BY public.fuel.id;

ALTER TABLE ONLY public.expenses
    ADD CONSTRAINT expenses_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.trips
    ADD CONSTRAINT trips_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.fuel
    ADD CONSTRAINT fuel_pkey PRIMARY KEY (id);
