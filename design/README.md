# Admin Frontend to Pencil Mockup

## Что найдено в `admin-frontend`

Проанализированы только файлы из `apps/admin-frontend/src`:

- Страницы: `LoginPage`, `DashboardPage`, `KnowledgeBasePage`, `QuestionsPage`
- Layout: `Layout`, `Sidebar`, `Header`
- Компоненты: `DataTable`, `Modal`, `ConfirmDialog`
- Токены и utility-классы: `index.css` (`btn-*`, `input`, `label`, `card`, `badge`)
- Состояния: loading spinner, empty blocks, confirm/edit/create dialogs, toast success/error

## Какой результат создан

Создан открываемый Pencil project:

- `design/mockup.epgz`

Исходные внутренние XML-страницы проекта оставлены в:

- `design/mockup_epgz/`

## Как открыть в Pencil

1. Открыть Desktop Pencil.
2. `File -> Open...`
3. Выбрать файл `design/mockup.epgz`.

Если конкретная версия Pencil не открывает `.epgz`, можно распаковать архив и переупаковать в `.epz`, сохранив `content.xml` в корне.

## Какие экраны включены

1. `01 Login`
2. `02 Dashboard`
3. `03 Knowledge Base`
4. `04 Questions Table`
5. `05 Question Dialogs`
6. `06 Settings and States` (derived screen in the same visual system)

## Ограничения и упрощения

- В `admin-frontend` нет отдельной страницы настроек, поэтому экран настроек сделан как производный (derived) с теми же токенами/паттернами.
- Иконки `lucide-react` переданы упрощенно (геометрические/текстовые аналоги).
- Интерактивность React-состояний (query/mutation, hover/focus/keyboard) заменена статическими визуальными состояниями.
- Toast-уведомления добавлены как placeholders, опираясь на `react-hot-toast` usage в исходных страницах.
- API/ошибки/динамика данных представлены в виде статических вариантов `loading/empty/error`.
