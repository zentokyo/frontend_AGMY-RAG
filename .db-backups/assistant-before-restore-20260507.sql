--
-- PostgreSQL database dump
--

\restrict 5jypRRHNcubhvACrDeTie6caNeFAORG48XbtR7jF8rEyyYTXZrlqItSL4kPgcqQ

-- Dumped from database version 17.9 (Homebrew)
-- Dumped by pg_dump version 17.9 (Homebrew)

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

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: update_app_users_updated_at(); Type: FUNCTION; Schema: public; Owner: elvsevolod
--

CREATE FUNCTION public.update_app_users_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_app_users_updated_at() OWNER TO elvsevolod;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admin_refresh_tokens; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.admin_refresh_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token_hash character varying(500) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.admin_refresh_tokens OWNER TO elvsevolod;

--
-- Name: admin_refresh_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: elvsevolod
--

CREATE SEQUENCE public.admin_refresh_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admin_refresh_tokens_id_seq OWNER TO elvsevolod;

--
-- Name: admin_refresh_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: elvsevolod
--

ALTER SEQUENCE public.admin_refresh_tokens_id_seq OWNED BY public.admin_refresh_tokens.id;


--
-- Name: admin_users; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.admin_users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(50) DEFAULT 'admin'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.admin_users OWNER TO elvsevolod;

--
-- Name: admin_users_id_seq; Type: SEQUENCE; Schema: public; Owner: elvsevolod
--

CREATE SEQUENCE public.admin_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admin_users_id_seq OWNER TO elvsevolod;

--
-- Name: admin_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: elvsevolod
--

ALTER SEQUENCE public.admin_users_id_seq OWNED BY public.admin_users.id;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO elvsevolod;

--
-- Name: answer; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.answer (
    answer_id uuid NOT NULL,
    exam_question_id uuid NOT NULL,
    answer_text character varying NOT NULL,
    is_correct boolean NOT NULL
);


ALTER TABLE public.answer OWNER TO elvsevolod;

--
-- Name: app_refresh_tokens; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.app_refresh_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token_hash character varying(500) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.app_refresh_tokens OWNER TO elvsevolod;

--
-- Name: app_refresh_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: elvsevolod
--

CREATE SEQUENCE public.app_refresh_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.app_refresh_tokens_id_seq OWNER TO elvsevolod;

--
-- Name: app_refresh_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: elvsevolod
--

ALTER SEQUENCE public.app_refresh_tokens_id_seq OWNED BY public.app_refresh_tokens.id;


--
-- Name: app_users; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.app_users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    username character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.app_users OWNER TO elvsevolod;

--
-- Name: app_users_id_seq; Type: SEQUENCE; Schema: public; Owner: elvsevolod
--

CREATE SEQUENCE public.app_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.app_users_id_seq OWNER TO elvsevolod;

--
-- Name: app_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: elvsevolod
--

ALTER SEQUENCE public.app_users_id_seq OWNED BY public.app_users.id;


--
-- Name: block_topic; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.block_topic (
    id integer NOT NULL,
    block_id integer NOT NULL,
    title character varying(255) NOT NULL,
    topic_order integer DEFAULT 0 NOT NULL,
    exam_theme_id uuid,
    theme_id uuid
);


ALTER TABLE public.block_topic OWNER TO postgres;

--
-- Name: block_topic_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.block_topic_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.block_topic_id_seq OWNER TO postgres;

--
-- Name: block_topic_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.block_topic_id_seq OWNED BY public.block_topic.id;


--
-- Name: course_block; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.course_block (
    id integer NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    block_order integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.course_block OWNER TO postgres;

--
-- Name: course_block_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.course_block_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.course_block_id_seq OWNER TO postgres;

--
-- Name: course_block_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.course_block_id_seq OWNED BY public.course_block.id;


--
-- Name: exam; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.exam (
    exam_id uuid NOT NULL,
    user_id integer NOT NULL,
    question_count integer NOT NULL,
    status character varying NOT NULL,
    start_exam timestamp without time zone NOT NULL,
    end_exam timestamp without time zone,
    exam_theme_id uuid NOT NULL,
    type character varying NOT NULL,
    rate character varying,
    exam_scope character varying(20) DEFAULT 'standalone'::character varying,
    block_topic_id integer,
    course_block_id integer
);


ALTER TABLE public.exam OWNER TO elvsevolod;

--
-- Name: exam_question; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.exam_question (
    exam_question_id uuid NOT NULL,
    exam_id uuid NOT NULL,
    question_id uuid NOT NULL,
    status character varying NOT NULL
);


ALTER TABLE public.exam_question OWNER TO elvsevolod;

--
-- Name: exam_theme; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.exam_theme (
    exam_theme_id uuid NOT NULL,
    title character varying NOT NULL,
    exam_theme_order integer NOT NULL
);


ALTER TABLE public.exam_theme OWNER TO elvsevolod;

--
-- Name: file; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.file (
    file_id uuid NOT NULL,
    filename character varying NOT NULL
);


ALTER TABLE public.file OWNER TO elvsevolod;

--
-- Name: question; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.question (
    question_id uuid NOT NULL,
    text character varying NOT NULL,
    theme_id uuid NOT NULL,
    answer_text character varying NOT NULL
);


ALTER TABLE public.question OWNER TO elvsevolod;

--
-- Name: theme; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.theme (
    theme_id uuid NOT NULL,
    title character varying NOT NULL,
    theme_order integer NOT NULL
);


ALTER TABLE public.theme OWNER TO elvsevolod;

--
-- Name: theme_file; Type: TABLE; Schema: public; Owner: elvsevolod
--

CREATE TABLE public.theme_file (
    theme_id uuid NOT NULL,
    file_id uuid NOT NULL
);


ALTER TABLE public.theme_file OWNER TO elvsevolod;

--
-- Name: user_block_progress; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_block_progress (
    id integer NOT NULL,
    user_id integer NOT NULL,
    block_id integer NOT NULL,
    status character varying(20) DEFAULT 'not_started'::character varying NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    best_score numeric(6,4) DEFAULT 0 NOT NULL,
    last_exam_id uuid,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.user_block_progress OWNER TO postgres;

--
-- Name: user_block_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_block_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_block_progress_id_seq OWNER TO postgres;

--
-- Name: user_block_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_block_progress_id_seq OWNED BY public.user_block_progress.id;


--
-- Name: user_course_progress; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_course_progress (
    id integer NOT NULL,
    user_id integer NOT NULL,
    status character varying(20) DEFAULT 'not_started'::character varying NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    best_score numeric(6,4) DEFAULT 0 NOT NULL,
    last_exam_id uuid,
    completed_at timestamp with time zone
);


ALTER TABLE public.user_course_progress OWNER TO postgres;

--
-- Name: user_course_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_course_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_course_progress_id_seq OWNER TO postgres;

--
-- Name: user_course_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_course_progress_id_seq OWNED BY public.user_course_progress.id;


--
-- Name: user_topic_progress; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_topic_progress (
    id integer NOT NULL,
    user_id integer NOT NULL,
    topic_id integer NOT NULL,
    status character varying(20) DEFAULT 'not_started'::character varying NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    best_score numeric(6,4) DEFAULT 0 NOT NULL,
    last_exam_id uuid,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.user_topic_progress OWNER TO postgres;

--
-- Name: user_topic_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_topic_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_topic_progress_id_seq OWNER TO postgres;

--
-- Name: user_topic_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_topic_progress_id_seq OWNED BY public.user_topic_progress.id;


--
-- Name: admin_refresh_tokens id; Type: DEFAULT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.admin_refresh_tokens ALTER COLUMN id SET DEFAULT nextval('public.admin_refresh_tokens_id_seq'::regclass);


--
-- Name: admin_users id; Type: DEFAULT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.admin_users ALTER COLUMN id SET DEFAULT nextval('public.admin_users_id_seq'::regclass);


--
-- Name: app_refresh_tokens id; Type: DEFAULT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.app_refresh_tokens ALTER COLUMN id SET DEFAULT nextval('public.app_refresh_tokens_id_seq'::regclass);


--
-- Name: app_users id; Type: DEFAULT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.app_users ALTER COLUMN id SET DEFAULT nextval('public.app_users_id_seq'::regclass);


--
-- Name: block_topic id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.block_topic ALTER COLUMN id SET DEFAULT nextval('public.block_topic_id_seq'::regclass);


--
-- Name: course_block id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_block ALTER COLUMN id SET DEFAULT nextval('public.course_block_id_seq'::regclass);


--
-- Name: user_block_progress id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_block_progress ALTER COLUMN id SET DEFAULT nextval('public.user_block_progress_id_seq'::regclass);


--
-- Name: user_course_progress id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_course_progress ALTER COLUMN id SET DEFAULT nextval('public.user_course_progress_id_seq'::regclass);


--
-- Name: user_topic_progress id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_topic_progress ALTER COLUMN id SET DEFAULT nextval('public.user_topic_progress_id_seq'::regclass);


--
-- Data for Name: admin_refresh_tokens; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.admin_refresh_tokens (id, user_id, token_hash, expires_at, created_at) FROM stdin;
1	1	22e638572379c08838ef63c5b00b0e4ae2b6e2c180bacdf0166376f444b0bf5a	2026-04-30 17:24:18.086902+07	2026-04-23 17:24:18.086902+07
3	1	bf326f275baa14038bec00f0c30b9f103607fae9a1e5f474918bda98c7d86707	2026-04-30 17:27:55.240208+07	2026-04-23 17:27:55.240208+07
9	1	fa3492784124a367836e03a2d3e238e5921085c444f1820c653623bc2fce0c98	2026-04-30 17:45:05.197826+07	2026-04-23 17:45:05.197826+07
11	1	ab42beda06874dd8da4bf5cab74f6201bbca1888be54a9cd3cc43cb17ed62478	2026-04-30 17:49:08.64637+07	2026-04-23 17:49:08.64637+07
12	1	e0edd7e17ab04dfb702796ba6a6382e39b9f968749cc53bcca621b33f77da216	2026-04-30 17:49:14.86041+07	2026-04-23 17:49:14.86041+07
161	1	ea7e970bada2df71cb203d2bd05be59d15d07f511fb7f7d8a32d7566f96371ea	2026-05-05 10:53:13.818777+07	2026-04-28 10:53:13.818777+07
167	1	0e02dc6bf0f0b8b2312c6c0f27abca14cd648ea3b0267930eca0010fc77b39ab	2026-05-05 11:28:05.048075+07	2026-04-28 11:28:05.048075+07
168	1	6e83417db2c4074b7d39b2b5976c557e8707aa175854295ffe766e4d3aacc1e4	2026-05-14 16:52:28.716307+07	2026-05-07 16:52:28.716307+07
\.


--
-- Data for Name: admin_users; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.admin_users (id, email, password_hash, role, created_at) FROM stdin;
1	admin@example.com	$2a$12$PTg4kNpwheDoLr2kicy99.MM3DcqXeYwAWjJTEXhajDt9r11VYely	admin	2026-04-23 17:23:57.623213+07
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.alembic_version (version_num) FROM stdin;
0cbd2fb19970
\.


--
-- Data for Name: answer; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.answer (answer_id, exam_question_id, answer_text, is_correct) FROM stdin;
\.


--
-- Data for Name: app_refresh_tokens; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.app_refresh_tokens (id, user_id, token_hash, expires_at, created_at) FROM stdin;
3	2	7e320dc50d1976fb22b862f3a16a1aa846d96ec18b5687ff1861819be5508d3d	2026-05-05 12:01:51.389283+07	2026-04-28 12:01:51.389283+07
6	4	936014826f2e2f8c43d0363103a0b0e73185b77f58c3d01ecf586a8bbd2bb616	2026-05-05 12:02:27.296151+07	2026-04-28 12:02:27.296151+07
9	6	92cd526072a57c8a81112169fdd41bfe981c8628551ad574f3f6007c97887b5a	2026-05-05 12:12:24.542163+07	2026-04-28 12:12:24.542163+07
10	7	ad74ae80fe5d1d4f34f06c934025370ba8eaa260dbcf8fd72c4846fc87c56fbc	2026-05-05 12:15:41.572364+07	2026-04-28 12:15:41.572364+07
14	8	ca5f538312111dd77df0e0b0ee1a9036999bb101a57eaa3bf333fc61b7abe782	2026-05-05 12:15:56.871823+07	2026-04-28 12:15:56.871823+07
18	9	527deb1bfe0d957b53f2dc551c8d39dfb7e3d6e5f1edb1de16a6de92be2caf1c	2026-05-05 12:16:29.23697+07	2026-04-28 12:16:29.23697+07
19	10	f6eb5000ca5c8cd9239f83c157d4f9557eba0d4963fe2142f4bc733ae80e38a0	2026-05-05 12:16:44.858283+07	2026-04-28 12:16:44.858283+07
22	12	603a316302a911c95c2d33d311d07a4fc32de583159f5eec5087201e13fc4d20	2026-05-05 12:16:54.800665+07	2026-04-28 12:16:54.800665+07
23	13	2fb84742ab44110439072ddff1fbc50d447409a672642d1d798edb9073e4940e	2026-05-05 12:23:25.428091+07	2026-04-28 12:23:25.428091+07
24	14	bf8be0bbb89a26c4f9a7f26cfcd89578e4c9b8d89241aad4b2bb80f9a71d58a9	2026-05-14 16:55:49.072956+07	2026-05-07 16:55:49.072956+07
25	14	27f16bfd191a3bd21f9c031e92c33fd72367eedaf22a912dcbd0a07cabf6ee4a	2026-05-14 16:55:51.795715+07	2026-05-07 16:55:51.795715+07
27	14	e2cfa9655b83b121a9daddf1c63eabc482b0d8ee16000bd9b00ce530a3538ba4	2026-05-14 17:01:20.378548+07	2026-05-07 17:01:20.378548+07
28	14	83587b02e0a3d6024a9b6786d9dba39561316f63c4d37e831da913226f11d19e	2026-05-14 17:01:40.179435+07	2026-05-07 17:01:40.179435+07
\.


--
-- Data for Name: app_users; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.app_users (id, email, password_hash, username, created_at, updated_at) FROM stdin;
1	e2e_1777352510910@example.com	$2a$12$/4bqfw75qI1CeW/MHARmWOWI6oEsxwBt14T6Y6bB8raNAiTQ9Lx8m	E2E User	2026-04-28 12:01:51.16093+07	2026-04-28 12:01:51.16093+07
2	e2e_exam_1777352511179@example.com	$2a$12$39GojrczB/vYo/sPlDyX/e6P97Lx36IsoMY2RvCouIVLQ8KPveERi	E2E Exam	2026-04-28 12:01:51.387897+07	2026-04-28 12:01:51.387897+07
3	e2e_1777352546849@example.com	$2a$12$bTUfAzn0zHhbAqCcuXwHOOHmvh51tF5FPFsuvqSwNRLNtZCx16boS	E2E User	2026-04-28 12:02:27.070406+07	2026-04-28 12:02:27.070406+07
4	e2e_exam_1777352547088@example.com	$2a$12$ctS15weT0kspoIZCMsmOUu/YNYyPoDPrNnR9L2aIx.rbVHROrOptC	E2E Exam	2026-04-28 12:02:27.294087+07	2026-04-28 12:02:27.294087+07
5	e2e_1777353144093@example.com	$2a$12$50fjJQcggPXqmdU6jgTo0e5zYpBsxlZevzUmfQ4BqPY9Lz0qNGxwS	E2E User	2026-04-28 12:12:24.313801+07	2026-04-28 12:12:24.313801+07
6	e2e_exam_1777353144331@example.com	$2a$12$hUyOTVhoB26C/Y7P3MHmJO5ha32Mc.WxTOBUhNT3mjVjRMZS2xewK	E2E Exam	2026-04-28 12:12:24.54023+07	2026-04-28 12:12:24.54023+07
7	ui_1777353341101@example.com	$2a$12$eMicGA3DoP.p71jDUC3LXuza7rc6izIJY6Y5bLKJXxMV0QyYBnocm	UI Tester	2026-04-28 12:15:41.568282+07	2026-04-28 12:15:41.568282+07
8	ui_1777353356296@example.com	$2a$12$GiGmJ.GDN/J0pedmLia/UOOPGiaDxWU3PKyB15x5ri7P.dBVORa8q	UI Tester	2026-04-28 12:15:56.665492+07	2026-04-28 12:15:56.665492+07
9	ui_1777353388387@example.com	$2a$12$pfBUhE3UkQbYS1.12.JeOuv8WnNZ.1ec/ariYeqjqc7HZvz/37A5m	UI Tester	2026-04-28 12:16:28.755755+07	2026-04-28 12:16:28.755755+07
10	ui_1777353404463@example.com	$2a$12$7/0nPZ4.pqpJegiNlaQkN.bNdqwXJlzE/.QzU8mJ1jhCa7B23O26.	UI Tester	2026-04-28 12:16:44.853967+07	2026-04-28 12:16:44.853967+07
11	e2e_1777353414362@example.com	$2a$12$1e7xznHuHWTH/KQWV/xxdO5HEmRwXDPYlN2Lmmx9z7VBURaPO4shG	E2E User	2026-04-28 12:16:54.579569+07	2026-04-28 12:16:54.579569+07
12	e2e_exam_1777353414595@example.com	$2a$12$142Re5M/tF6aHwn8g1ZMBuRg3fHGyxSgcf/DAS45paCmL57at.tAq	E2E Exam	2026-04-28 12:16:54.79898+07	2026-04-28 12:16:54.79898+07
13	admin@example.com	$2a$12$udOIMoSMmW47/o9uLqViAeVUH4GptwxOm.FAJP/J3jPWm7Ro5svsC	Иван	2026-04-28 12:23:25.422173+07	2026-04-28 12:23:25.422173+07
14	chat@example.com	$2a$12$sOihcCjGQ0ymulw9oyP7FuZhIR4N1lJTioI6.5nPcFxRMRNF2Ngju	chatuser	2026-05-07 16:55:49.068459+07	2026-05-07 16:55:49.068459+07
\.


--
-- Data for Name: block_topic; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.block_topic (id, block_id, title, topic_order, exam_theme_id, theme_id) FROM stdin;
5	1	Эпидемиология гемоконтактных инфекций (ГВ, ГС, ВИЧ-инфекция)	5	99fa4b2f-6b30-4340-9b50-0fdd58ffaf87	0fc0d715-391a-4f40-b101-dd1a8c8fc796
6	2	Особенности вакцинации против ВГВ	1	09233269-08e2-41e1-8cef-9f225544ea38	2c2648bc-c732-42bb-bae5-cd40175df68e
7	2	Профилактика профессионального заражения	2	4fc1f2d9-bf9d-4b62-b8c1-dd8fb0fc4e71	dfe35959-636d-4e0e-b52b-588e0402b068
8	2	Соблюдение правил регистрации аварийной ситуации на рабочем месте при проведении медицинских манипуляций	3	95d91c88-bffe-4897-b13f-2469bff2b848	f4df4dd4-3781-4369-bd9a-3f5ccb70884f
9	2	Итоговый экзамен	4	20c07372-f0f7-4b9a-8fb8-e120ea1e6b56	\N
10	2	Test Theme	5	\N	\N
11	3	Тест	1	\N	\N
2	1	E2E Theme	2	\N	\N
3	1	E2E Theme	3	\N	\N
4	1	E2E Theme	4	\N	\N
1	1	E2E Theme	1	\N	\N
12	3	E2E UI Theme	2	\N	\N
15	3	E2E UI Theme	5	\N	\N
14	3	E2E UI Theme	4	\N	\N
13	3	E2E UI Theme	3	\N	\N
\.


--
-- Data for Name: course_block; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.course_block (id, title, description, block_order) FROM stdin;
1	Блок 1	\N	1
2	Блок 2	\N	2
3	Блок 3	\N	3
\.


--
-- Data for Name: exam; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.exam (exam_id, user_id, question_count, status, start_exam, end_exam, exam_theme_id, type, rate, exam_scope, block_topic_id, course_block_id) FROM stdin;
\.


--
-- Data for Name: exam_question; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.exam_question (exam_question_id, exam_id, question_id, status) FROM stdin;
\.


--
-- Data for Name: exam_theme; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.exam_theme (exam_theme_id, title, exam_theme_order) FROM stdin;
99fa4b2f-6b30-4340-9b50-0fdd58ffaf87	Эпидемиология гемоконтактных инфекций (ГВ, ГС, ВИЧ-инфекция)	1
09233269-08e2-41e1-8cef-9f225544ea38	Особенности вакцинации против ВГВ	2
4fc1f2d9-bf9d-4b62-b8c1-dd8fb0fc4e71	Профилактика профессионального заражения	3
95d91c88-bffe-4897-b13f-2469bff2b848	Соблюдение правил регистрации аварийной ситуации на рабочем месте при проведении медицинских манипуляций	4
20c07372-f0f7-4b9a-8fb8-e120ea1e6b56	Итоговый экзамен	5
\.


--
-- Data for Name: file; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.file (file_id, filename) FROM stdin;
4cbfe8fa-e36d-49ae-aa6a-00d6c697d1a5	Blok_1_Epidemiologiia_gemokontaktnykh_infektsii_.pdf
f1015e9c-dffe-4173-a23d-e310687a81cf	Blok_2_Osobennosti_vaktsinatsii_protiv_VGV_.pdf
3fb43ff0-d3a3-4b70-9db1-b03c81464eb7	Blok_3_Profilaktika_professional'nogo_zarazheniia_.pdf
cab7205d-8110-4644-9e05-4c34d4348896	Prikaz VICh AK No. 277 2024 god.pdf
db966701-96fe-4d9f-b591-d44cf0adaef9	Blok_4_Sobliudenie_pravil_registratsii_avariinoi_situatsii_na_rabochem.pdf
42cd9ce4-1489-4a50-9791-42632c43d697	Prikaz VICh AK No. 277 2024 god.pdf
dacbc064-c521-43bc-8e66-0a5c6feba8f1	3_________________________________________________________________________.docx
\.


--
-- Data for Name: question; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.question (question_id, text, theme_id, answer_text) FROM stdin;
cf917239-bf8a-4e61-9668-aceae9f53a36	Что понимается под термином «гемоконтактные инфекции» в профессиональном риске медицинских работников?	0fc0d715-391a-4f40-b101-dd1a8c8fc796	Гемоконтактные инфекции (ГКИ) – это инфекционные заболевания, возбудители которых передаются при контакте с инфицированной кровью и другими биологическими жидкостями организма. Наибольший профессиональный риск для медработников представляют вирусные гепатиты В (ВГВ), С (ВГС) и ВИЧ-инфекция.
d3f0e5a8-7aeb-4629-bce9-7cfed75f4020	Назовите основные биологические жидкости, представляющие наибольшую эпидемиологическую опасность в плане заражения ГКИ.	0fc0d715-391a-4f40-b101-dd1a8c8fc796	Наибольшую опасность представляет кровь и ее компоненты. Высокий риск также связан со спермой, вагинальным секретом и любыми биологическими жидкостями с видимой примесью крови. Слюна, моча, ликвор и плевральная жидкость считаются потенциально опасными, особенно при попадании на поврежденную кожу или слизистые оболочки.
309f39a9-f39a-4591-a39c-43133e580d5c	Какой из вирусов (ВГВ, ВГС, ВИЧ) является наиболее устойчивым во внешней среде и обладает наибольшей контагиозностью при профессиональном заражении?	0fc0d715-391a-4f40-b101-dd1a8c8fc796	Наиболее устойчив и контагиозен вирус гепатита В (ВГВ). Инфицирующая доза составляет всего 0,0000001 мл сыворотки, содержащей вирус.
5e0ed977-7d70-4521-9bf1-c0c0146952b8	Что является основным методом профилактики профессионального инфицирования вирусным гепатитом В?	2c2648bc-c732-42bb-bae5-cd40175df68e	Основным и наиболее эффективным методом является профилактическая иммунизация (вакцинация) против гепатита В. В соответствии с Федеральным законом № 157-ФЗ «Об иммунопрофилактике инфекционных болезней», СанПиН 3.3686-21 'санитарно-эпидемиологические требования по профилактике инфекционных болезней', вакцинация против гепатита В является обязательной для всех медицинских работников, относящихся к группе риска.
32ddac6b-4aeb-4077-b55a-fe58ca4ab59c	Напишите цифрами схему вакцинации (во сколько месяцев ставится прививка) против вирусного гепатита В (не для ребёнка группы риска). 	2c2648bc-c732-42bb-bae5-cd40175df68e	0 (первые 24 часа жизни) -1-6 месяцев.
12d83bf4-11b8-4000-a58f-dc591b33440f	Напишите цифрами схему вакцинации (во сколько месяцев ставится прививка) против вирусного гепатита В (для ребёнка группы риска).	2c2648bc-c732-42bb-bae5-cd40175df68e	0 (первые 24 часа жизни) -1-2-12 месяцев.
ff3db23e-81e1-454a-bce1-394f1ae253fd	Каковы первоочередные действия медработника при попадании биологической жидкости на спец. одежду / обувь?	dfe35959-636d-4e0e-b52b-588e0402b068	Снять рабочую одежду и погрузить в дезинфицирующий раствор или в герметичном мешке направить для стирки с дезинфекцией в прачечную, осуществляющую стирку больничного белья.
eb719ed6-bcec-43ec-9054-914079b20666	Каковы первоочередные действия медработника непосредственно в момент получения травмы (укола, пореза)?	dfe35959-636d-4e0e-b52b-588e0402b068	Немедленно снять перчатки, вымыть руки с мылом под проточной водой, обработать руки 70%-м спиртом, смазать ранку 5%-м спиртовым раствором йода. Сообщить о происшествии непосредственному руководителю и ответственному за профилактику профессионального заражения.
9e06133f-4db3-44af-bf4c-3443e58cc73e	Каков алгоритм действий медработника при попадании крови или других биологических жидкостей пациента на кожные покровы?	dfe35959-636d-4e0e-b52b-588e0402b068	1. Обработать место загрязнения 70% этиловым спиртом.\n2. Вымыть руки под проточной водой с мылом и повторно обработать 70% этиловым спиртом.\n3. Не тереть!
cdc73fcd-7ab0-490e-865b-1d209155d75b	Каков алгоритм действий медработника при попадании биологических жидкостей на слизистые оболочки (глаза, нос, рот)?	dfe35959-636d-4e0e-b52b-588e0402b068	Обильно промыть водой, не тереть. Немедленно обратиться к ответственному лицу для регистрации аварийной ситуации.
7ffbc226-0117-4ddd-b495-574fcb9b4e71	Какая информация должна быть немедленно установлена в отношении пациента, чьи биологические жидкости стали источником аварийной ситуации?	dfe35959-636d-4e0e-b52b-588e0402b068	Необходимо установить: • ФИО, историю болезни.\n• Его инфекционный статус по ГКИ (наличие маркеров HBsAg, anti-HCV, anti-HIV).\n• Если статус неизвестен, необходимо с его информированного согласия провести экспресс-тестирование на ВИЧ и маркеры вирусных гепатитов.
e2a66357-e3a6-4b0f-9027-5d929f7f7bdf	Каковы сроки проведения экстренной профилактики ВИЧ-инфекции после аварийной ситуации?	dfe35959-636d-4e0e-b52b-588e0402b068	Экстренная профилактика (постконтактная профилактика, ПКП) антиретровирусными препаратами должна быть начата в течение первых 2 часов после аварии, но не позднее 72 часов. Назначение проводит врач-инфекционист или врач центра СПИД.
0a50a30f-0fca-46a0-bd96-7843fdef74fa	Каков порядок диспансерного наблюдения за медработником, пострадавшим в аварийной ситуации с риском заражения ВИЧ?	dfe35959-636d-4e0e-b52b-588e0402b068	Обследование на anti-HIV методом ИФА проводится сразу после аварии, затем через 3, 6 и 12 месяцев. В течение всего периода наблюдения (12 месяцев) медработник должен соблюдать меры предосторожности, чтобы не стать потенциальным источником инфекции для других (использование барьерных методов контрацепции, отказ от донорства и т.д.).
172d3054-3044-41db-8a34-f9f7d3ae71b1	Что такое «Стандартные меры предосторожности» и какова их роль?	f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Стандартные меры предосторожности – это комплекс мероприятий, выполняемых медицинским персоналом при работе со всеми пациентами, независимо от известного или предполагаемого инфекционного статуса. Они включают: гигиену рук, использование СИЗ (перчатки, маски, экраны, халаты), безопасное обращение с острым инструментарием, правильную обработку медицинских отходов и др. Их соблюдение – основа профилактики профессионального инфицирования.
3685fed3-84d1-46b5-8afb-7753227f7810	Что в соответствии с нормативными документами считается «аварийной ситуацией» на рабочем месте медработника?	f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Аварийной ситуацией считается любое событие, создавшее риск профессионального заражения ГКИ: травмы (уколы, порезы) инструментарием, контаминированным биоматериалом пациента, попадание крови или других биологических жидкостей на слизистые оболочки или поврежденную кожу.
79f6f4f7-35f7-480a-8265-25b5da52d506	Какой основной документ регламентирует действия при аварийной ситуации в медицинской организации?	f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Внутренние локальные акты МО, разработанные на основе СанПиН 3.3686-21 «Санитарно-эпидемиологические требования по профилактике инфекционных болезней», Приказа Минздрава России № 408н «Об утверждении Порядка проведения обязательных предварительных и периодических медицинских осмотров работников» и методических указаний МУ 3.1.2313-08 «Требования к обеззараживанию, уничтожению и утилизации шприцев инъекционных однократного применения», Приказа Министерства Здравоохренения Алтайского края № 277 от 14.06.2024 г. «Об организации мероприятий по профилактике инфицирования ВИЧ инфекции у медицинских работников».
7e292cfa-c9ea-4811-8195-6eb12cc8b7c9	Кто в медицинской организации несет ответственность за организацию профилактики профессионального инфицирования и расследование аварийных ситуаций?	f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Ответственность несет руководитель медицинской организации (главный врач). Непосредственно организацию и контроль осуществляет ответственное лицо, назначенное приказом (часто – заместитель главного врача по лечебной работе или по эпидемиологическим вопросам, старшая медсестра). В каждом подразделении должен быть ответственный из числа старшего персонала.
2b58efc7-0aff-402d-b7da-c4a139294cda	Каков правовой статус медработника, заразившегося ГКИ на рабочем месте?	f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Случай профессионального заражения ГКИ при выполнении трудовых обязанностей при правильном оформлении расследования признается несчастным случаем на производстве. Это дает право медработнику на получение страховых выплат, возмещение вреда здоровью и иные компенсации в соответствии с Федеральным законом № 125-ФЗ «Об обязательном социальном страховании от несчастных случаев на производстве и профессиональных заболеваний».
\.


--
-- Data for Name: theme; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.theme (theme_id, title, theme_order) FROM stdin;
0fc0d715-391a-4f40-b101-dd1a8c8fc796	Эпидемиология гемоконтактных инфекций (ГВ, ГС, ВИЧ-инфекция)	1
2c2648bc-c732-42bb-bae5-cd40175df68e	Особенности вакцинации против ВГВ	2
dfe35959-636d-4e0e-b52b-588e0402b068	Профилактика профессионального заражения	3
f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Соблюдение правил регистрации аварийной ситуации на рабочем месте при проведении медицинских манипуляций	4
\.


--
-- Data for Name: theme_file; Type: TABLE DATA; Schema: public; Owner: elvsevolod
--

COPY public.theme_file (theme_id, file_id) FROM stdin;
0fc0d715-391a-4f40-b101-dd1a8c8fc796	4cbfe8fa-e36d-49ae-aa6a-00d6c697d1a5
2c2648bc-c732-42bb-bae5-cd40175df68e	f1015e9c-dffe-4173-a23d-e310687a81cf
dfe35959-636d-4e0e-b52b-588e0402b068	3fb43ff0-d3a3-4b70-9db1-b03c81464eb7
dfe35959-636d-4e0e-b52b-588e0402b068	cab7205d-8110-4644-9e05-4c34d4348896
f4df4dd4-3781-4369-bd9a-3f5ccb70884f	db966701-96fe-4d9f-b591-d44cf0adaef9
f4df4dd4-3781-4369-bd9a-3f5ccb70884f	42cd9ce4-1489-4a50-9791-42632c43d697
0fc0d715-391a-4f40-b101-dd1a8c8fc796	dacbc064-c521-43bc-8e66-0a5c6feba8f1
\.


--
-- Data for Name: user_block_progress; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_block_progress (id, user_id, block_id, status, attempts, best_score, last_exam_id, updated_at) FROM stdin;
\.


--
-- Data for Name: user_course_progress; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_course_progress (id, user_id, status, attempts, best_score, last_exam_id, completed_at) FROM stdin;
\.


--
-- Data for Name: user_topic_progress; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_topic_progress (id, user_id, topic_id, status, attempts, best_score, last_exam_id, updated_at) FROM stdin;
1	14	1	failed	1	0.0000	dd58fa6a-b980-493f-afa9-094955ba4f66	2026-05-07 16:56:31.45807+07
\.


--
-- Name: admin_refresh_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: elvsevolod
--

SELECT pg_catalog.setval('public.admin_refresh_tokens_id_seq', 168, true);


--
-- Name: admin_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: elvsevolod
--

SELECT pg_catalog.setval('public.admin_users_id_seq', 5, true);


--
-- Name: app_refresh_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: elvsevolod
--

SELECT pg_catalog.setval('public.app_refresh_tokens_id_seq', 28, true);


--
-- Name: app_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: elvsevolod
--

SELECT pg_catalog.setval('public.app_users_id_seq', 14, true);


--
-- Name: block_topic_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.block_topic_id_seq', 15, true);


--
-- Name: course_block_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.course_block_id_seq', 3, true);


--
-- Name: user_block_progress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_block_progress_id_seq', 1, false);


--
-- Name: user_course_progress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_course_progress_id_seq', 1, false);


--
-- Name: user_topic_progress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_topic_progress_id_seq', 1, true);


--
-- Name: admin_refresh_tokens admin_refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.admin_refresh_tokens
    ADD CONSTRAINT admin_refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: admin_users admin_users_email_key; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_email_key UNIQUE (email);


--
-- Name: admin_users admin_users_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: answer answer_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.answer
    ADD CONSTRAINT answer_pkey PRIMARY KEY (answer_id);


--
-- Name: app_refresh_tokens app_refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.app_refresh_tokens
    ADD CONSTRAINT app_refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: app_users app_users_email_key; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.app_users
    ADD CONSTRAINT app_users_email_key UNIQUE (email);


--
-- Name: app_users app_users_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.app_users
    ADD CONSTRAINT app_users_pkey PRIMARY KEY (id);


--
-- Name: block_topic block_topic_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.block_topic
    ADD CONSTRAINT block_topic_pkey PRIMARY KEY (id);


--
-- Name: course_block course_block_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_block
    ADD CONSTRAINT course_block_pkey PRIMARY KEY (id);


--
-- Name: exam exam_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_pkey PRIMARY KEY (exam_id);


--
-- Name: exam_question exam_question_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.exam_question
    ADD CONSTRAINT exam_question_pkey PRIMARY KEY (exam_question_id);


--
-- Name: exam_theme exam_theme_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.exam_theme
    ADD CONSTRAINT exam_theme_pkey PRIMARY KEY (exam_theme_id);


--
-- Name: file file_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.file
    ADD CONSTRAINT file_pkey PRIMARY KEY (file_id);


--
-- Name: question question_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_pkey PRIMARY KEY (question_id);


--
-- Name: theme_file theme_file_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.theme_file
    ADD CONSTRAINT theme_file_pkey PRIMARY KEY (theme_id, file_id);


--
-- Name: theme theme_pkey; Type: CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.theme
    ADD CONSTRAINT theme_pkey PRIMARY KEY (theme_id);


--
-- Name: user_block_progress user_block_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_block_progress
    ADD CONSTRAINT user_block_progress_pkey PRIMARY KEY (id);


--
-- Name: user_block_progress user_block_progress_user_id_block_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_block_progress
    ADD CONSTRAINT user_block_progress_user_id_block_id_key UNIQUE (user_id, block_id);


--
-- Name: user_course_progress user_course_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_course_progress
    ADD CONSTRAINT user_course_progress_pkey PRIMARY KEY (id);


--
-- Name: user_course_progress user_course_progress_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_course_progress
    ADD CONSTRAINT user_course_progress_user_id_key UNIQUE (user_id);


--
-- Name: user_topic_progress user_topic_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_topic_progress
    ADD CONSTRAINT user_topic_progress_pkey PRIMARY KEY (id);


--
-- Name: user_topic_progress user_topic_progress_user_id_topic_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_topic_progress
    ADD CONSTRAINT user_topic_progress_user_id_topic_id_key UNIQUE (user_id, topic_id);


--
-- Name: idx_admin_refresh_tokens_hash; Type: INDEX; Schema: public; Owner: elvsevolod
--

CREATE INDEX idx_admin_refresh_tokens_hash ON public.admin_refresh_tokens USING btree (token_hash);


--
-- Name: idx_admin_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: elvsevolod
--

CREATE INDEX idx_admin_refresh_tokens_user_id ON public.admin_refresh_tokens USING btree (user_id);


--
-- Name: idx_app_refresh_tokens_hash; Type: INDEX; Schema: public; Owner: elvsevolod
--

CREATE INDEX idx_app_refresh_tokens_hash ON public.app_refresh_tokens USING btree (token_hash);


--
-- Name: idx_app_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: elvsevolod
--

CREATE INDEX idx_app_refresh_tokens_user_id ON public.app_refresh_tokens USING btree (user_id);


--
-- Name: idx_app_users_email; Type: INDEX; Schema: public; Owner: elvsevolod
--

CREATE INDEX idx_app_users_email ON public.app_users USING btree (email);


--
-- Name: app_users trigger_update_app_users_updated_at; Type: TRIGGER; Schema: public; Owner: elvsevolod
--

CREATE TRIGGER trigger_update_app_users_updated_at BEFORE UPDATE ON public.app_users FOR EACH ROW EXECUTE FUNCTION public.update_app_users_updated_at();


--
-- Name: admin_refresh_tokens admin_refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.admin_refresh_tokens
    ADD CONSTRAINT admin_refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.admin_users(id) ON DELETE CASCADE;


--
-- Name: answer answer_exam_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.answer
    ADD CONSTRAINT answer_exam_question_id_fkey FOREIGN KEY (exam_question_id) REFERENCES public.exam_question(exam_question_id);


--
-- Name: app_refresh_tokens app_refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.app_refresh_tokens
    ADD CONSTRAINT app_refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;


--
-- Name: block_topic block_topic_block_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.block_topic
    ADD CONSTRAINT block_topic_block_id_fkey FOREIGN KEY (block_id) REFERENCES public.course_block(id) ON DELETE CASCADE;


--
-- Name: block_topic block_topic_exam_theme_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.block_topic
    ADD CONSTRAINT block_topic_exam_theme_id_fkey FOREIGN KEY (exam_theme_id) REFERENCES public.exam_theme(exam_theme_id) ON DELETE SET NULL;


--
-- Name: block_topic block_topic_theme_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.block_topic
    ADD CONSTRAINT block_topic_theme_id_fkey FOREIGN KEY (theme_id) REFERENCES public.theme(theme_id) ON DELETE SET NULL;


--
-- Name: exam exam_block_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_block_topic_id_fkey FOREIGN KEY (block_topic_id) REFERENCES public.block_topic(id) ON DELETE SET NULL;


--
-- Name: exam exam_course_block_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_course_block_id_fkey FOREIGN KEY (course_block_id) REFERENCES public.course_block(id) ON DELETE SET NULL;


--
-- Name: exam exam_exam_theme_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_exam_theme_id_fkey FOREIGN KEY (exam_theme_id) REFERENCES public.exam_theme(exam_theme_id);


--
-- Name: exam_question exam_question_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.exam_question
    ADD CONSTRAINT exam_question_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exam(exam_id);


--
-- Name: exam_question exam_question_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.exam_question
    ADD CONSTRAINT exam_question_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.question(question_id);


--
-- Name: question question_theme_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_theme_id_fkey FOREIGN KEY (theme_id) REFERENCES public.theme(theme_id);


--
-- Name: theme_file theme_file_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.theme_file
    ADD CONSTRAINT theme_file_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.file(file_id);


--
-- Name: theme_file theme_file_theme_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: elvsevolod
--

ALTER TABLE ONLY public.theme_file
    ADD CONSTRAINT theme_file_theme_id_fkey FOREIGN KEY (theme_id) REFERENCES public.theme(theme_id);


--
-- Name: user_block_progress user_block_progress_block_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_block_progress
    ADD CONSTRAINT user_block_progress_block_id_fkey FOREIGN KEY (block_id) REFERENCES public.course_block(id) ON DELETE CASCADE;


--
-- Name: user_block_progress user_block_progress_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_block_progress
    ADD CONSTRAINT user_block_progress_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;


--
-- Name: user_course_progress user_course_progress_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_course_progress
    ADD CONSTRAINT user_course_progress_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;


--
-- Name: user_topic_progress user_topic_progress_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_topic_progress
    ADD CONSTRAINT user_topic_progress_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.block_topic(id) ON DELETE CASCADE;


--
-- Name: user_topic_progress user_topic_progress_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_topic_progress
    ADD CONSTRAINT user_topic_progress_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.app_users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 5jypRRHNcubhvACrDeTie6caNeFAORG48XbtR7jF8rEyyYTXZrlqItSL4kPgcqQ

