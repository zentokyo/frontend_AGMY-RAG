# Component Inventory (`admin-frontend` -> Pencil)

## Layout and Navigation

- `apps/admin-frontend/src/components/Layout/Layout.jsx`  
  Преобразовано в: основной shell с `sidebar + topbar + content`.

- `apps/admin-frontend/src/components/Layout/Sidebar.jsx`  
  Преобразовано в: левый темный sidebar с brand-блоком, active nav item, footer version.

- `apps/admin-frontend/src/components/Layout/Header.jsx`  
  Преобразовано в: верхний header с user chip, role badge, logout button.

## Pages

- `apps/admin-frontend/src/pages/LoginPage.jsx`  
  Преобразовано в: центрированная auth-card, email/password fields, primary CTA, loading/toast placeholders.

- `apps/admin-frontend/src/pages/DashboardPage.jsx`  
  Преобразовано в: 4 stat cards, recent uploads list, Q&amp;A by themes panel.

- `apps/admin-frontend/src/pages/KnowledgeBasePage.jsx`  
  Преобразовано в: theme rows, actions (add files/delete), empty state, create-theme modal with upload progress.

- `apps/admin-frontend/src/pages/QuestionsPage.jsx`  
  Преобразовано в: filters (search + theme), data table, pagination, view/edit/delete flow.

## Reusable Components

- `apps/admin-frontend/src/components/Table/DataTable.jsx`  
  Преобразовано в: table shell (header row, body rows, loading/empty row placeholders).

- `apps/admin-frontend/src/components/Modal/Modal.jsx`  
  Преобразовано в: centered overlay dialog with title bar and body.

- `apps/admin-frontend/src/components/Modal/ConfirmDialog.jsx`  
  Преобразовано в: compact destructive confirmation dialog with cancel/delete actions.

## Design Tokens (from `index.css`)

- `apps/admin-frontend/src/index.css`  
  Извлечено и визуально применено:
  - buttons: `btn-primary`, `btn-secondary`, `btn-danger`
  - inputs/labels: `input`, `label`
  - cards/badges: `card`, `badge`
  - базовые цвета: slate palette + blue-600 + red-600
  - скругления: преимущественно 8/10/12 px

## State Coverage in Pencil Mockup

- loading: spinner/progress placeholders
- empty: no-data blocks for knowledge base/table
- error: toast error placeholders
- modal: create/edit/view/confirm dialog variants
- table/form/dashboard/filter/detail/settings views included
