"""Seed canonical course content.

Revision ID: a1b2c3d4e5f6
Revises: f0b1c2d3e4f5
Create Date: 2026-06-14
"""

from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CANONICAL_BLOCK = {
    "title": "Блок 1",
    "description": None,
    "order": 1,
}

CANONICAL_THEMES = [
    {
        "theme_id": "0fc0d715-391a-4f40-b101-dd1a8c8fc796",
        "exam_theme_id": "99fa4b2f-6b30-4340-9b50-0fdd58ffaf87",
        "order": 1,
        "title": "Эпидемиология гемоконтактных инфекций (ГВ, ГС, ВИЧ-инфекция)",
        "questions": [
            {
                "question_id": "cf917239-bf8a-4e61-9668-aceae9f53a36",
                "text": "Что понимается под термином «гемоконтактные инфекции» в профессиональном риске медицинских работников?",
                "answer": "Гемоконтактные инфекции (ГКИ) – это инфекционные заболевания, возбудители которых передаются при контакте с инфицированной кровью и другими биологическими жидкостями организма. Наибольший профессиональный риск для медработников представляют вирусные гепатиты В (ВГВ), С (ВГС) и ВИЧ-инфекция.",
            },
            {
                "question_id": "d3f0e5a8-7aeb-4629-bce9-7cfed75f4020",
                "text": "Назовите основные биологические жидкости, представляющие наибольшую эпидемиологическую опасность в плане заражения ГКИ.",
                "answer": "Наибольшую опасность представляет кровь и ее компоненты. Высокий риск также связан со спермой, вагинальным секретом и любыми биологическими жидкостями с видимой примесью крови. Слюна, моча, ликвор и плевральная жидкость считаются потенциально опасными, особенно при попадании на поврежденную кожу или слизистые оболочки.",
            },
            {
                "question_id": "309f39a9-f39a-4591-a39c-43133e580d5c",
                "text": "Какой из вирусов (ВГВ, ВГС, ВИЧ) является наиболее устойчивым во внешней среде и обладает наибольшей контагиозностью при профессиональном заражении?",
                "answer": "Наиболее устойчив и контагиозен вирус гепатита В (ВГВ). Инфицирующая доза составляет всего 0,0000001 мл сыворотки, содержащей вирус.",
            },
        ],
    },
    {
        "theme_id": "2c2648bc-c732-42bb-bae5-cd40175df68e",
        "exam_theme_id": "09233269-08e2-41e1-8cef-9f225544ea38",
        "order": 2,
        "title": "Особенности вакцинации против ВГВ",
        "questions": [
            {
                "question_id": "5e0ed977-7d70-4521-9bf1-c0c0146952b8",
                "text": "Что является основным методом профилактики профессионального инфицирования вирусным гепатитом В?",
                "answer": "Основным и наиболее эффективным методом является профилактическая иммунизация (вакцинация) против гепатита В. В соответствии с Федеральным законом № 157-ФЗ «Об иммунопрофилактике инфекционных болезней», СанПиН 3.3686-21 'санитарно-эпидемиологические требования по профилактике инфекционных болезней', вакцинация против гепатита В является обязательной для всех медицинских работников, относящихся к группе риска.",
            },
            {
                "question_id": "32ddac6b-4aeb-4077-b55a-fe58ca4ab59c",
                "text": "Напишите цифрами схему вакцинации (во сколько месяцев ставится прививка) против вирусного гепатита В (не для ребёнка группы риска).",
                "answer": "0 (первые 24 часа жизни) -1-6 месяцев.",
            },
            {
                "question_id": "12d83bf4-11b8-4000-a58f-dc591b33440f",
                "text": "Напишите цифрами схему вакцинации (во сколько месяцев ставится прививка) против вирусного гепатита В (для ребёнка группы риска).",
                "answer": "0 (первые 24 часа жизни) -1-2-12 месяцев.",
            },
        ],
    },
    {
        "theme_id": "dfe35959-636d-4e0e-b52b-588e0402b068",
        "exam_theme_id": "4fc1f2d9-bf9d-4b62-b8c1-dd8fb0fc4e71",
        "order": 3,
        "title": "Профилактика профессионального заражения",
        "questions": [
            {
                "question_id": "ff3db23e-81e1-454a-bce1-394f1ae253fd",
                "text": "Каковы первоочередные действия медработника при попадании биологической жидкости на спец. одежду / обувь?",
                "answer": "При попадании крови или другой биологической жидкости на халат или рабочую одежду необходимо снять загрязненную одежду и погрузить ее в дезинфицирующий раствор либо поместить в бикс (бак) для автоклавирования. Загрязненную обувь обрабатывают дезинфицирующим средством: двукратно протирают тампоном, смоченным дезраствором. После снятия одежды загрязненные участки кожи обрабатывают 70% спиртом, промывают водой с мылом и повторно обрабатывают 70% спиртом.",
            },
            {
                "question_id": "eb719ed6-bcec-43ec-9054-914079b20666",
                "text": "Каковы первоочередные действия медработника непосредственно в момент получения травмы (укола, пореза)?",
                "answer": "Немедленно снять перчатки, вымыть руки с мылом под проточной водой, обработать руки 70%-м спиртом, смазать ранку 5%-м спиртовым раствором йода. Сообщить о происшествии непосредственному руководителю и ответственному за профилактику профессионального заражения.",
            },
            {
                "question_id": "9e06133f-4db3-44af-bf4c-3443e58cc73e",
                "text": "Каков алгоритм действий медработника при попадании крови или других биологических жидкостей пациента на кожные покровы?",
                "answer": "1. Обработать место загрязнения 70% этиловым спиртом.\n2. Вымыть руки под проточной водой с мылом и повторно обработать 70% этиловым спиртом.\n3. Не тереть!",
            },
            {
                "question_id": "cdc73fcd-7ab0-490e-865b-1d209155d75b",
                "text": "Каков алгоритм действий медработника при попадании биологических жидкостей на слизистые оболочки (глаза, нос, рот)?",
                "answer": "Обильно промыть водой, не тереть. Немедленно обратиться к ответственному лицу для регистрации аварийной ситуации.",
            },
            {
                "question_id": "7ffbc226-0117-4ddd-b495-574fcb9b4e71",
                "text": "Какая информация должна быть немедленно установлена в отношении пациента, чьи биологические жидкости стали источником аварийной ситуации?",
                "answer": "Необходимо установить: • ФИО, историю болезни.\n• Его инфекционный статус по ГКИ (наличие маркеров HBsAg, anti-HCV, anti-HIV).\n• Если статус неизвестен, необходимо с его информированного согласия провести экспресс-тестирование на ВИЧ и маркеры вирусных гепатитов.",
            },
            {
                "question_id": "e2a66357-e3a6-4b0f-9027-5d929f7f7bdf",
                "text": "Каковы сроки проведения экстренной профилактики ВИЧ-инфекции после аварийной ситуации?",
                "answer": "Экстренная профилактика (постконтактная профилактика, ПКП) антиретровирусными препаратами должна быть начата в течение первых 2 часов после аварии, но не позднее 72 часов. Назначение проводит врач-инфекционист или врач центра СПИД.",
            },
            {
                "question_id": "0a50a30f-0fca-46a0-bd96-7843fdef74fa",
                "text": "Каков порядок диспансерного наблюдения за медработником, пострадавшим в аварийной ситуации с риском заражения ВИЧ?",
                "answer": "Обследование на anti-HIV методом ИФА проводится сразу после аварии, затем через 3, 6 и 12 месяцев. В течение всего периода наблюдения (12 месяцев) медработник должен соблюдать меры предосторожности, чтобы не стать потенциальным источником инфекции для других (использование барьерных методов контрацепции, отказ от донорства и т.д.).",
            },
        ],
    },
    {
        "theme_id": "f4df4dd4-3781-4369-bd9a-3f5ccb70884f",
        "exam_theme_id": "95d91c88-bffe-4897-b13f-2469bff2b848",
        "order": 4,
        "title": "Соблюдение правил регистрации аварийной ситуации на рабочем месте при проведении медицинских манипуляций",
        "questions": [
            {
                "question_id": "172d3054-3044-41db-8a34-f9f7d3ae71b1",
                "text": "Что такое «Стандартные меры предосторожности» и какова их роль?",
                "answer": "Стандартные меры предосторожности – это комплекс мероприятий, выполняемых медицинским персоналом при работе со всеми пациентами, независимо от известного или предполагаемого инфекционного статуса. Они включают: гигиену рук, использование СИЗ (перчатки, маски, экраны, халаты), безопасное обращение с острым инструментарием, правильную обработку медицинских отходов и др. Их соблюдение – основа профилактики профессионального инфицирования.",
            },
            {
                "question_id": "3685fed3-84d1-46b5-8afb-7753227f7810",
                "text": "Что в соответствии с нормативными документами считается «аварийной ситуацией» на рабочем месте медработника?",
                "answer": "Аварийной ситуацией считается любое событие, создавшее риск профессионального заражения ГКИ: травмы (уколы, порезы) инструментарием, контаминированным биоматериалом пациента, попадание крови или других биологических жидкостей на слизистые оболочки или поврежденную кожу.",
            },
            {
                "question_id": "79f6f4f7-35f7-480a-8265-25b5da52d506",
                "text": "Какой основной документ регламентирует действия при аварийной ситуации в медицинской организации?",
                "answer": "Основной федеральный документ, регламентирующий действия при аварийной ситуации, — СанПиН 3.3686-21 «Санитарно-эпидемиологические требования по профилактике инфекционных болезней». В медицинской организации действия также закрепляются внутренними локальными актами, разработанными на его основе, и региональным приказом Министерства здравоохранения Алтайского края №277 от 14.06.2024 «Об организации мероприятий по профилактике инфицирования ВИЧ инфекции у медицинских работников».",
            },
            {
                "question_id": "7e292cfa-c9ea-4811-8195-6eb12cc8b7c9",
                "text": "Кто в медицинской организации несет ответственность за организацию профилактики профессионального инфицирования и расследование аварийных ситуаций?",
                "answer": "Ответственность несет руководитель медицинской организации (главный врач). Непосредственно организацию и контроль осуществляет ответственное лицо, назначенное приказом (часто – заместитель главного врача по лечебной работе или по эпидемиологическим вопросам, старшая медсестра). В каждом подразделении должен быть ответственный из числа старшего персонала.",
            },
            {
                "question_id": "2b58efc7-0aff-402d-b7da-c4a139294cda",
                "text": "Каков правовой статус медработника, заразившегося ГКИ на рабочем месте?",
                "answer": "Случай заражения медработника ГКИ, связанный с исполнением трудовых обязанностей и подтвержденный расследованием, квалифицируется как профессиональное заболевание. Для подтверждения связи инфекции с работой проводится эпидемиологическое расследование и составляется акт о случае профессионального заболевания. Если аварийная ситуация сопровождалась травмой, переводом на другую работу, утратой трудоспособности или смертью, дополнительно оформляется акт о несчастном случае на производстве.",
            },
        ],
    },
]


def upgrade() -> None:
    connection = op.get_bind()
    block_id = _ensure_block(connection, CANONICAL_BLOCK)
    _delete_empty_generated_topics(connection)

    for theme in CANONICAL_THEMES:
        theme_id = _ensure_theme(connection, theme)
        exam_theme_id = _ensure_exam_theme(connection, theme)
        _ensure_block_topic(connection, block_id, theme_id, exam_theme_id, theme)
        for question in theme["questions"]:
            _upsert_question(connection, theme_id, question)


def downgrade() -> None:
    # The migration updates seed content; downgrading should not erase admin edits.
    pass


def _first(connection: Any, statement: str, params: dict[str, object] | None = None) -> Any | None:
    params = params or {}
    return connection.execute(sa.text(statement), params).mappings().first()


def _ensure_block(connection: Any, block: dict[str, object]) -> int:
    row = _first(
        connection,
        "SELECT id FROM course_block WHERE title = :title ORDER BY block_order ASC LIMIT 1",
        {"title": block["title"]},
    )
    if row:
        connection.execute(
            sa.text(
                """
                UPDATE course_block
                SET description = :description,
                    block_order = :block_order
                WHERE id = :id
                """
            ),
            {"id": row["id"], "description": block["description"], "block_order": block["order"]},
        )
        return int(row["id"])

    inserted = _first(
        connection,
        """
        INSERT INTO course_block (title, description, block_order)
        VALUES (:title, :description, :block_order)
        RETURNING id
        """,
        {"title": block["title"], "description": block["description"], "block_order": block["order"]},
    )
    if not inserted:
        raise RuntimeError("Failed to seed canonical course block")
    return int(inserted["id"])


def _delete_empty_generated_topics(connection: Any) -> None:
    connection.execute(
        sa.text(
            """
            DELETE FROM block_topic
            WHERE theme_id IS NULL
              AND exam_theme_id IS NULL
            """
        )
    )


def _ensure_theme(connection: Any, theme: dict[str, object]) -> str:
    row = _first(
        connection,
        "SELECT theme_id FROM theme WHERE title = :title ORDER BY theme_order ASC LIMIT 1",
        {"title": theme["title"]},
    )
    if row:
        connection.execute(
            sa.text(
                """
                UPDATE theme
                SET theme_order = :theme_order
                WHERE theme_id = CAST(:theme_id AS uuid)
                """
            ),
            {"theme_id": str(row["theme_id"]), "theme_order": theme["order"]},
        )
        return str(row["theme_id"])

    inserted = _first(
        connection,
        """
        INSERT INTO theme (theme_id, title, theme_order)
        VALUES (CAST(:theme_id AS uuid), :title, :theme_order)
        ON CONFLICT (theme_id) DO UPDATE
        SET title = EXCLUDED.title,
            theme_order = EXCLUDED.theme_order
        RETURNING theme_id
        """,
        {"theme_id": theme["theme_id"], "title": theme["title"], "theme_order": theme["order"]},
    )
    if not inserted:
        raise RuntimeError(f"Failed to seed theme: {theme['title']}")
    return str(inserted["theme_id"])


def _ensure_exam_theme(connection: Any, theme: dict[str, object]) -> str:
    row = _first(
        connection,
        "SELECT exam_theme_id FROM exam_theme WHERE title = :title ORDER BY exam_theme_order ASC LIMIT 1",
        {"title": theme["title"]},
    )
    if row:
        connection.execute(
            sa.text(
                """
                UPDATE exam_theme
                SET exam_theme_order = :exam_theme_order
                WHERE exam_theme_id = CAST(:exam_theme_id AS uuid)
                """
            ),
            {"exam_theme_id": str(row["exam_theme_id"]), "exam_theme_order": theme["order"]},
        )
        return str(row["exam_theme_id"])

    inserted = _first(
        connection,
        """
        INSERT INTO exam_theme (exam_theme_id, title, exam_theme_order)
        VALUES (CAST(:exam_theme_id AS uuid), :title, :exam_theme_order)
        ON CONFLICT (exam_theme_id) DO UPDATE
        SET title = EXCLUDED.title,
            exam_theme_order = EXCLUDED.exam_theme_order
        RETURNING exam_theme_id
        """,
        {
            "exam_theme_id": theme["exam_theme_id"],
            "title": theme["title"],
            "exam_theme_order": theme["order"],
        },
    )
    if not inserted:
        raise RuntimeError(f"Failed to seed exam theme: {theme['title']}")
    return str(inserted["exam_theme_id"])


def _ensure_block_topic(
    connection: Any,
    block_id: int,
    theme_id: str,
    exam_theme_id: str,
    theme: dict[str, object],
) -> None:
    row = _first(
        connection,
        """
        SELECT id
        FROM block_topic
        WHERE theme_id = CAST(:theme_id AS uuid)
           OR exam_theme_id = CAST(:exam_theme_id AS uuid)
        ORDER BY topic_order ASC, id ASC
        LIMIT 1
        """,
        {"theme_id": theme_id, "exam_theme_id": exam_theme_id},
    )
    if row:
        connection.execute(
            sa.text(
                """
                UPDATE block_topic
                SET block_id = :block_id,
                    title = :title,
                    topic_order = :topic_order,
                    exam_theme_id = CAST(:exam_theme_id AS uuid),
                    theme_id = CAST(:theme_id AS uuid)
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "block_id": block_id,
                "title": theme["title"],
                "topic_order": theme["order"],
                "exam_theme_id": exam_theme_id,
                "theme_id": theme_id,
            },
        )
        return

    connection.execute(
        sa.text(
            """
            INSERT INTO block_topic (block_id, title, topic_order, exam_theme_id, theme_id)
            VALUES (
                :block_id,
                :title,
                :topic_order,
                CAST(:exam_theme_id AS uuid),
                CAST(:theme_id AS uuid)
            )
            """
        ),
        {
            "block_id": block_id,
            "title": theme["title"],
            "topic_order": theme["order"],
            "exam_theme_id": exam_theme_id,
            "theme_id": theme_id,
        },
    )


def _upsert_question(connection: Any, theme_id: str, question: dict[str, str]) -> None:
    row = _first(
        connection,
        """
        SELECT question_id
        FROM question
        WHERE theme_id = CAST(:theme_id AS uuid)
          AND btrim(text) = btrim(:text)
        ORDER BY question_id ASC
        LIMIT 1
        """,
        {"theme_id": theme_id, "text": question["text"]},
    )
    if row:
        connection.execute(
            sa.text(
                """
                UPDATE question
                SET text = :text,
                    answer_text = :answer_text
                WHERE question_id = CAST(:question_id AS uuid)
                """
            ),
            {
                "question_id": str(row["question_id"]),
                "text": question["text"],
                "answer_text": question["answer"],
            },
        )
        return

    connection.execute(
        sa.text(
            """
            INSERT INTO question (question_id, theme_id, text, answer_text)
            VALUES (
                CAST(:question_id AS uuid),
                CAST(:theme_id AS uuid),
                :text,
                :answer_text
            )
            ON CONFLICT (question_id) DO UPDATE
            SET theme_id = EXCLUDED.theme_id,
                text = EXCLUDED.text,
                answer_text = EXCLUDED.answer_text
            """
        ),
        {
            "question_id": question["question_id"],
            "theme_id": theme_id,
            "text": question["text"],
            "answer_text": question["answer"],
        },
    )
