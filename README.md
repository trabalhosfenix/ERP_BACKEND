# ERP Backend - Gestão de Pedidos

API REST para operações de ERP (clientes, produtos, pedidos e autenticação), construída com Django REST Framework, com foco em consistência transacional, idempotência e controle de permissões por perfil.

## Stack
- Python 3.12
- Django + Django REST Framework
- MySQL 8 (padrão) / SQLite (testes locais)
- Redis 7 (rate limit e suporte de idempotência)
- Docker / Docker Compose
- Pytest
- OpenAPI/Swagger (`/docs`) e Redoc (`/redoc`)

## Módulos funcionais
- **Autenticação e usuários** (JWT, sessão, cadastro e gestão de usuários)
- **Clientes** (cadastro e consulta)
- **Produtos** (cadastro, consulta e atualização de estoque)
- **Pedidos** (criação idempotente, consulta, cancelamento e transição de status)
- **Infra comum** (soft delete, paginação, permissões por perfil, rate limit e health check)

## Endpoints da API (v1)
Base path: `/api/v1`

### Health e documentação
- `GET /health`
- `GET /docs`
- `GET /redoc`
- `GET /api/schema`

### Autenticação
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/jwt/login`
- `POST /api/v1/auth/jwt/refresh`
- `POST /api/v1/auth/session/login`
- `POST /api/v1/auth/session/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/users`
- `POST /api/v1/auth/users`
- `PATCH /api/v1/auth/users/:id`

### Clientes
- `POST /api/v1/customers`
- `GET /api/v1/customers`
- `GET /api/v1/customers/:id`

### Produtos
- `POST /api/v1/products`
- `GET /api/v1/products`
- `PATCH /api/v1/products/:id/stock`

### Pedidos
- `POST /api/v1/orders`
- `GET /api/v1/orders`
- `GET /api/v1/orders/:id`
- `PATCH /api/v1/orders/:id/status` ← **rota de alteração de status garantida**
- `DELETE /api/v1/orders/:id` (cancelamento com reversão de estoque)

> Implementação de rota: o backend aceita a atualização de status por `PATCH /api/v1/orders/<id>/status`, mantendo compatibilidade com o contrato documentado em `:id`.

## Regras de negócio implementadas

### Pedidos
- Criação exige `customer_id`, `idempotency_key` e itens com `product_id` + `qty`.
- Criação idempotente por cliente + `idempotency_key`.
- Retry idempotente retorna o mesmo pedido (sem duplicidade).
- Controle de estoque é atômico em transação.
- Bloqueio pessimista (`select_for_update`) para concorrência.
- Cancelamento só permitido quando status está em `PENDENTE` ou `CONFIRMADO`.
- Cancelamento devolve estoque dos itens.

### Fluxo de status
Estados válidos:
- `PENDENTE`
- `CONFIRMADO`
- `SEPARADO`
- `ENVIADO`
- `ENTREGUE`
- `CANCELADO`

Transições válidas:
- `PENDENTE -> CONFIRMADO | CANCELADO`
- `CONFIRMADO -> SEPARADO | CANCELADO`
- `SEPARADO -> ENVIADO`
- `ENVIADO -> ENTREGUE`
- `ENTREGUE` e `CANCELADO` não possuem saída

Endpoint:
- `PATCH /api/v1/orders/:id/status`
- Payload:
  ```json
  {
    "status": "CONFIRMADO",
    "note": "opcional"
  }
  ```

### Permissões por perfil
Perfis usados via grupos do Django: `admin`, `manager`, `operator`, `viewer`.

- Leitura (`GET`) de clientes/produtos/pedidos: todos os perfis.
- Criação de clientes/produtos: `admin`, `manager`.
- Criação de pedidos e patch de status: `admin`, `manager`, `operator`.
- Cancelamento de pedido: `admin`, `manager`.
- Gestão de usuários (`/auth/users`): `admin` e `manager`.
- Superuser possui acesso irrestrito.

### Recursos transversais
- Soft delete (`deleted_at`) em entidades críticas.
- Paginação padrão por `limit/offset`.
- Busca/ordenação em endpoints de listagem.
- Rate limit por IP para `/api/*` via Redis.
- Histórico de status (`order_status_history`).
- Domain events de mudança de status (`order_domain_events`).

## Como rodar localmente (Docker)
```bash
cp .env.example .env
docker compose up --build
```

URLs principais:
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`

## Rodando testes localmente
```bash
cd backend
DB_ENGINE=sqlite python manage.py migrate
cd ..
DB_ENGINE=sqlite pytest
```

## Estrutura de pastas
- `backend/apps/authentication` autenticação, sessão, JWT e gestão de usuários
- `backend/apps/customers` domínio de clientes
- `backend/apps/products` domínio de produtos
- `backend/apps/orders` domínio de pedidos, serviços e regras de status
- `backend/apps/common` componentes compartilhados
- `backend/config` configuração Django e roteamento raiz
- `tests/` testes unitários e de integração
- `frontend/` template simples para interação manual

## Decisões arquiteturais
Veja `ARCHITECTURE.md` para visão técnica completa (camadas, transações, idempotência, concorrência, eventos e compatibilidade).
