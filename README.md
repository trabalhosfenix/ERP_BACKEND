# ERP Backend - Gestão de Pedidos

API REST em Django REST Framework para módulo de pedidos de ERP, com foco em consistência transacional, idempotência e concorrência de estoque.

## Stack
- Python 3.12
- Django + DRF
- MySQL 8
- Redis 7
- Docker / Docker Compose
- Pytest
- OpenAPI/Swagger (`/docs`)

## Requisitos implementados
- Endpoints de clientes, produtos e pedidos em `/api/v1`
- Controle de estoque atômico com `transaction.atomic` + `select_for_update`
- Idempotência de criação de pedido por `idempotency_key` (DB + Redis)
- Fluxo de status com validação de transições
- Histórico de status
- Domain events para transição de status (publicação e consumo)
- Autenticação por JWT e por sessão
- Permissões por perfil (admin, manager, operator, viewer)
- Soft delete (`deleted_at`) para entidades críticas
- Paginação, busca e ordenação nos endpoints de listagem
- Rate limiting básico via Redis por IP
- Health check em `/health`

## Endpoints principais
- `POST /api/v1/customers`
- `GET /api/v1/customers`
- `GET /api/v1/customers/:id`
- `POST /api/v1/products`
- `GET /api/v1/products`
- `PATCH /api/v1/products/:id/stock`
- `POST /api/v1/orders`
- `GET /api/v1/orders`
- `GET /api/v1/orders/:id`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/jwt/login`
- `POST /api/v1/auth/jwt/refresh`
- `POST /api/v1/auth/session/login`
- `POST /api/v1/auth/session/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/users`
- `POST /api/v1/auth/users`
- `PATCH /api/v1/auth/users/:id`
- `PATCH /api/v1/orders/:id/status`
- `DELETE /api/v1/orders/:id`

## Como rodar localmente
```bash
cp .env.example .env
docker compose up --build
```

Swagger: `http://localhost:8000/docs`

## Rodando testes
```bash
cd backend
DB_ENGINE=sqlite python manage.py migrate
cd ..
DB_ENGINE=sqlite pytest
```

## Estrutura
- `backend/` código fonte
- `tests/` testes unitários e integração
- `docker-compose.yml`
- `Dockerfile`
- `.env.example`
- `ARCHITECTURE.md`

## Decisões arquiteturais
Ver `ARCHITECTURE.md`.


## Frontend (template)
- O template base está em `frontend/index.html` com estilos em `frontend/css/style.css` e lógica em `frontend/js/app.js`.
- Inclui fluxo de login, criação de login, logout e setor de usuários com permissões por perfil.
