--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5 (Debian 17.5-1.pgdg130+1)
-- Dumped by pg_dump version 17.5 (Debian 17.5-1.pgdg130+1)

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
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: answer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.answer (
    answer_id uuid NOT NULL,
    exam_question_id uuid NOT NULL,
    answer_text character varying NOT NULL,
    is_correct boolean,
    evaluation_status character varying(32) DEFAULT 'done'::character varying NOT NULL,
    evaluation_method character varying(64),
    evaluation_error text
);


ALTER TABLE public.answer OWNER TO postgres;

--
-- Name: exam; Type: TABLE; Schema: public; Owner: postgres
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
    rate character varying
);


ALTER TABLE public.exam OWNER TO postgres;

--
-- Name: exam_question; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exam_question (
    exam_question_id uuid NOT NULL,
    exam_id uuid NOT NULL,
    question_id uuid NOT NULL,
    status character varying NOT NULL
);


ALTER TABLE public.exam_question OWNER TO postgres;

--
-- Name: exam_theme; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exam_theme (
    exam_theme_id uuid NOT NULL,
    title character varying NOT NULL,
    exam_theme_order integer NOT NULL
);


ALTER TABLE public.exam_theme OWNER TO postgres;

--
-- Name: question; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.question (
    question_id uuid NOT NULL,
    text character varying NOT NULL,
    theme_id uuid NOT NULL,
    answer_text character varying NOT NULL
);


ALTER TABLE public.question OWNER TO postgres;

--
-- Name: file; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.file (
    file_id uuid NOT NULL,
    filename character varying NOT NULL
);


ALTER TABLE public.file OWNER TO postgres;

--
-- Name: theme; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.theme (
    theme_id uuid NOT NULL,
    title character varying NOT NULL,
    theme_order integer NOT NULL
);


ALTER TABLE public.theme OWNER TO postgres;

--
-- Name: theme_file; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.theme_file (
    theme_id uuid NOT NULL,
    file_id uuid NOT NULL
);


ALTER TABLE public.theme_file OWNER TO postgres;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
0cbd2fb19970
\.


--
-- Data for Name: answer; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.answer (answer_id, exam_question_id, answer_text, is_correct, evaluation_status, evaluation_method, evaluation_error) FROM stdin;
\.


--
-- Data for Name: exam; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.exam (exam_id, user_id, question_count, status, start_exam, end_exam, exam_theme_id, type) FROM stdin;
\.


--
-- Data for Name: exam_question; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.exam_question (exam_question_id, exam_id, question_id, status) FROM stdin;
\.


--
-- Data for Name: exam_theme; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.exam_theme (exam_theme_id, title, exam_theme_order) FROM stdin;
99fa4b2f-6b30-4340-9b50-0fdd58ffaf87	Эпидемиология гемоконтактных инфекций (ГВ, ГС, ВИЧ-инфекция)	1
09233269-08e2-41e1-8cef-9f225544ea38	Особенности вакцинации против ВГВ	2
4fc1f2d9-bf9d-4b62-b8c1-dd8fb0fc4e71	Профилактика профессионального заражения	3
95d91c88-bffe-4897-b13f-2469bff2b848	Соблюдение правил регистрации аварийной ситуации на рабочем месте при проведении медицинских манипуляций	4
20c07372-f0f7-4b9a-8fb8-e120ea1e6b56	Итоговый экзамен	5
\.

--
-- Data for Name: file; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.file (file_id, filename) FROM stdin;
4cbfe8fa-e36d-49ae-aa6a-00d6c697d1a5	Blok_1_Epidemiologiia_gemokontaktnykh_infektsii_.pdf
f1015e9c-dffe-4173-a23d-e310687a81cf	Blok_2_Osobennosti_vaktsinatsii_protiv_VGV_.pdf
3fb43ff0-d3a3-4b70-9db1-b03c81464eb7	Blok_3_Profilaktika_professional'nogo_zarazheniia_.pdf
cab7205d-8110-4644-9e05-4c34d4348896	Prikaz VICh AK No. 277 2024 god.pdf
db966701-96fe-4d9f-b591-d44cf0adaef9	Blok_4_Sobliudenie_pravil_registratsii_avariinoi_situatsii_na_rabochem.pdf
42cd9ce4-1489-4a50-9791-42632c43d697	Prikaz VICh AK No. 277 2024 god.pdf
\.

--
-- Data for Name: question; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.question (question_id, text, theme_id, answer_text) FROM stdin;
cf917239-bf8a-4e61-9668-aceae9f53a36	Что понимается под термином «гемоконтактные инфекции» в профессиональном риске медицинских работников?	0fc0d715-391a-4f40-b101-dd1a8c8fc796	Гемоконтактные инфекции (ГКИ) – это инфекционные заболевания, возбудители которых передаются при контакте с инфицированной кровью и другими биологическими жидкостями организма. Наибольший профессиональный риск для медработников представляют вирусные гепатиты В (ВГВ), С (ВГС) и ВИЧ-инфекция.
d3f0e5a8-7aeb-4629-bce9-7cfed75f4020	Назовите основные биологические жидкости, представляющие наибольшую эпидемиологическую опасность в плане заражения ГКИ.	0fc0d715-391a-4f40-b101-dd1a8c8fc796	Наибольшую опасность представляет кровь и ее компоненты. Высокий риск также связан со спермой, вагинальным секретом и любыми биологическими жидкостями с видимой примесью крови. Слюна, моча, ликвор и плевральная жидкость считаются потенциально опасными, особенно при попадании на поврежденную кожу или слизистые оболочки.
309f39a9-f39a-4591-a39c-43133e580d5c	Какой из вирусов (ВГВ, ВГС, ВИЧ) является наиболее устойчивым во внешней среде и обладает наибольшей контагиозностью при профессиональном заражении?	0fc0d715-391a-4f40-b101-dd1a8c8fc796	Наиболее устойчив и контагиозен вирус гепатита В (ВГВ). Инфицирующая доза составляет всего 0,0000001 мл сыворотки, содержащей вирус.
5e0ed977-7d70-4521-9bf1-c0c0146952b8	Что является основным методом профилактики профессионального инфицирования вирусным гепатитом В?	2c2648bc-c732-42bb-bae5-cd40175df68e	Основным и наиболее эффективным методом является профилактическая иммунизация (вакцинация) против гепатита В. В соответствии с Федеральным законом № 157-ФЗ «Об иммунопрофилактике инфекционных болезней», СанПиН 3.3686-21 'санитарно-эпидемиологические требования по профилактике инфекционных болезней', вакцинация против гепатита В является обязательной для всех медицинских работников, относящихся к группе риска.
32ddac6b-4aeb-4077-b55a-fe58ca4ab59c	Напишите цифрами схему вакцинации (во сколько месяцев ставится прививка) против вирусного гепатита В (не для ребёнка группы риска). 	2c2648bc-c732-42bb-bae5-cd40175df68e	0 (первые 24 часа жизни) -1-6 месяцев.
12d83bf4-11b8-4000-a58f-dc591b33440f	Напишите цифрами схему вакцинации (во сколько месяцев ставится прививка) против вирусного гепатита В (для ребёнка группы риска).	2c2648bc-c732-42bb-bae5-cd40175df68e	0 (первые 24 часа жизни) -1-2-12 месяцев.
ff3db23e-81e1-454a-bce1-394f1ae253fd	Каковы первоочередные действия медработника при попадании биологической жидкости на спец. одежду / обувь?	dfe35959-636d-4e0e-b52b-588e0402b068	При попадании крови или другой биологической жидкости на халат или рабочую одежду необходимо снять загрязненную одежду и погрузить ее в дезинфицирующий раствор либо поместить в бикс (бак) для автоклавирования. Загрязненную обувь обрабатывают дезинфицирующим средством: двукратно протирают тампоном, смоченным дезраствором. После снятия одежды загрязненные участки кожи обрабатывают 70% спиртом, промывают водой с мылом и повторно обрабатывают 70% спиртом.
eb719ed6-bcec-43ec-9054-914079b20666	Каковы первоочередные действия медработника непосредственно в момент получения травмы (укола, пореза)?	dfe35959-636d-4e0e-b52b-588e0402b068	Немедленно снять перчатки, вымыть руки с мылом под проточной водой, обработать руки 70%-м спиртом, смазать ранку 5%-м спиртовым раствором йода. Сообщить о происшествии непосредственному руководителю и ответственному за профилактику профессионального заражения.
9e06133f-4db3-44af-bf4c-3443e58cc73e	Каков алгоритм действий медработника при попадании крови или других биологических жидкостей пациента на кожные покровы?	dfe35959-636d-4e0e-b52b-588e0402b068	1. Обработать место загрязнения 70% этиловым спиртом.\n2. Вымыть руки под проточной водой с мылом и повторно обработать 70% этиловым спиртом.\n3. Не тереть!
cdc73fcd-7ab0-490e-865b-1d209155d75b	Каков алгоритм действий медработника при попадании биологических жидкостей на слизистые оболочки (глаза, нос, рот)?	dfe35959-636d-4e0e-b52b-588e0402b068	Обильно промыть водой, не тереть. Немедленно обратиться к ответственному лицу для регистрации аварийной ситуации.
7ffbc226-0117-4ddd-b495-574fcb9b4e71	Какая информация должна быть немедленно установлена в отношении пациента, чьи биологические жидкости стали источником аварийной ситуации?	dfe35959-636d-4e0e-b52b-588e0402b068	Необходимо установить: • ФИО, историю болезни.\n• Его инфекционный статус по ГКИ (наличие маркеров HBsAg, anti-HCV, anti-HIV).\n• Если статус неизвестен, необходимо с его информированного согласия провести экспресс-тестирование на ВИЧ и маркеры вирусных гепатитов.
e2a66357-e3a6-4b0f-9027-5d929f7f7bdf	Каковы сроки проведения экстренной профилактики ВИЧ-инфекции после аварийной ситуации?	dfe35959-636d-4e0e-b52b-588e0402b068	Экстренная профилактика (постконтактная профилактика, ПКП) антиретровирусными препаратами должна быть начата в течение первых 2 часов после аварии, но не позднее 72 часов. Назначение проводит врач-инфекционист или врач центра СПИД.
0a50a30f-0fca-46a0-bd96-7843fdef74fa	Каков порядок диспансерного наблюдения за медработником, пострадавшим в аварийной ситуации с риском заражения ВИЧ?	dfe35959-636d-4e0e-b52b-588e0402b068	Обследование на anti-HIV методом ИФА проводится сразу после аварии, затем через 3, 6 и 12 месяцев. В течение всего периода наблюдения (12 месяцев) медработник должен соблюдать меры предосторожности, чтобы не стать потенциальным источником инфекции для других (использование барьерных методов контрацепции, отказ от донорства и т.д.).
172d3054-3044-41db-8a34-f9f7d3ae71b1	Что такое «Стандартные меры предосторожности» и какова их роль?	f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Стандартные меры предосторожности – это комплекс мероприятий, выполняемых медицинским персоналом при работе со всеми пациентами, независимо от известного или предполагаемого инфекционного статуса. Они включают: гигиену рук, использование СИЗ (перчатки, маски, экраны, халаты), безопасное обращение с острым инструментарием, правильную обработку медицинских отходов и др. Их соблюдение – основа профилактики профессионального инфицирования.
3685fed3-84d1-46b5-8afb-7753227f7810	Что в соответствии с нормативными документами считается «аварийной ситуацией» на рабочем месте медработника?	f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Аварийной ситуацией считается любое событие, создавшее риск профессионального заражения ГКИ: травмы (уколы, порезы) инструментарием, контаминированным биоматериалом пациента, попадание крови или других биологических жидкостей на слизистые оболочки или поврежденную кожу.
79f6f4f7-35f7-480a-8265-25b5da52d506	Какой основной документ регламентирует действия при аварийной ситуации в медицинской организации?	f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Основной федеральный документ, регламентирующий действия при аварийной ситуации, — СанПиН 3.3686-21 «Санитарно-эпидемиологические требования по профилактике инфекционных болезней». В медицинской организации действия также закрепляются внутренними локальными актами, разработанными на его основе, и региональным приказом Министерства здравоохранения Алтайского края №277 от 14.06.2024 «Об организации мероприятий по профилактике инфицирования ВИЧ инфекции у медицинских работников».
7e292cfa-c9ea-4811-8195-6eb12cc8b7c9	Кто в медицинской организации несет ответственность за организацию профилактики профессионального инфицирования и расследование аварийных ситуаций?	f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Ответственность несет руководитель медицинской организации (главный врач). Непосредственно организацию и контроль осуществляет ответственное лицо, назначенное приказом (часто – заместитель главного врача по лечебной работе или по эпидемиологическим вопросам, старшая медсестра). В каждом подразделении должен быть ответственный из числа старшего персонала.
2b58efc7-0aff-402d-b7da-c4a139294cda	Каков правовой статус медработника, заразившегося ГКИ на рабочем месте?	f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Случай заражения медработника ГКИ, связанный с исполнением трудовых обязанностей и подтвержденный расследованием, квалифицируется как профессиональное заболевание. Для подтверждения связи инфекции с работой проводится эпидемиологическое расследование и составляется акт о случае профессионального заболевания. Если аварийная ситуация сопровождалась травмой, переводом на другую работу, утратой трудоспособности или смертью, дополнительно оформляется акт о несчастном случае на производстве.
\.


--
-- Data for Name: theme; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.theme (theme_id, title, theme_order) FROM stdin;
0fc0d715-391a-4f40-b101-dd1a8c8fc796	Эпидемиология гемоконтактных инфекций (ГВ, ГС, ВИЧ-инфекция)	1
2c2648bc-c732-42bb-bae5-cd40175df68e	Особенности вакцинации против ВГВ	2
dfe35959-636d-4e0e-b52b-588e0402b068	Профилактика профессионального заражения	3
f4df4dd4-3781-4369-bd9a-3f5ccb70884f	Соблюдение правил регистрации аварийной ситуации на рабочем месте при проведении медицинских манипуляций	4
\.

--
-- Data for Name: theme_file; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.theme_file (theme_id, file_id) FROM stdin;
0fc0d715-391a-4f40-b101-dd1a8c8fc796	4cbfe8fa-e36d-49ae-aa6a-00d6c697d1a5
2c2648bc-c732-42bb-bae5-cd40175df68e	f1015e9c-dffe-4173-a23d-e310687a81cf
dfe35959-636d-4e0e-b52b-588e0402b068	3fb43ff0-d3a3-4b70-9db1-b03c81464eb7
dfe35959-636d-4e0e-b52b-588e0402b068	cab7205d-8110-4644-9e05-4c34d4348896
f4df4dd4-3781-4369-bd9a-3f5ccb70884f	db966701-96fe-4d9f-b591-d44cf0adaef9
f4df4dd4-3781-4369-bd9a-3f5ccb70884f	42cd9ce4-1489-4a50-9791-42632c43d697
\.

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: answer answer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answer
    ADD CONSTRAINT answer_pkey PRIMARY KEY (answer_id);


--
-- Name: exam exam_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_pkey PRIMARY KEY (exam_id);


--
-- Name: exam_question exam_question_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_question
    ADD CONSTRAINT exam_question_pkey PRIMARY KEY (exam_question_id);


--
-- Name: exam_theme exam_theme_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_theme
    ADD CONSTRAINT exam_theme_pkey PRIMARY KEY (exam_theme_id);

--
-- Name: file file_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.file
    ADD CONSTRAINT file_pkey PRIMARY KEY (file_id);


--
-- Name: question question_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_pkey PRIMARY KEY (question_id);

--
-- Name: theme_file theme_file_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.theme_file
    ADD CONSTRAINT theme_file_pkey PRIMARY KEY (theme_id, file_id);



--
-- Name: theme theme_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.theme
    ADD CONSTRAINT theme_pkey PRIMARY KEY (theme_id);


--
-- Name: answer answer_exam_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.answer
    ADD CONSTRAINT answer_exam_question_id_fkey FOREIGN KEY (exam_question_id) REFERENCES public.exam_question(exam_question_id);


--
-- Name: exam exam_exam_theme_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam
    ADD CONSTRAINT exam_exam_theme_id_fkey FOREIGN KEY (exam_theme_id) REFERENCES public.exam_theme(exam_theme_id);


--
-- Name: exam_question exam_question_exam_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_question
    ADD CONSTRAINT exam_question_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exam(exam_id);


--
-- Name: exam_question exam_question_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_question
    ADD CONSTRAINT exam_question_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.question(question_id);


--
-- Name: question question_theme_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT question_theme_id_fkey FOREIGN KEY (theme_id) REFERENCES public.theme(theme_id);

--
-- Name: theme_file theme_file_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.theme_file
    ADD CONSTRAINT theme_file_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.file(file_id);


--
-- Name: theme_file theme_file_theme_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.theme_file
    ADD CONSTRAINT theme_file_theme_id_fkey FOREIGN KEY (theme_id) REFERENCES public.theme(theme_id);



--
-- PostgreSQL database dump complete
--
