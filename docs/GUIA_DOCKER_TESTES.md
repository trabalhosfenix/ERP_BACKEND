# Guia rápido: inicialização e testes em Docker

Este guia cobre:
1. Subir o ambiente completo (MySQL + Redis + API).
2. Validar saúde da aplicação.
3. Executar testes automatizados.
4. Rodar um **smoke test ponta a ponta** (auth + cadastro + pedido + alteração de status).

## 1) Pré-requisitos
- Docker e Docker Compose instalados.
- Porta `8000` (API), `3306` (MySQL) e `6379` (Redis) livres.

## 2) Inicialização do ambiente

### 2.1 Preparar variáveis
```bash
cp .env.example .env
```

### 2.2 Subir os containers
```bash
docker compose up --build -d
```

### 2.3 Acompanhar logs até estabilizar
```bash
docker compose logs -f backend
```

Critérios de sucesso esperados:
- backend informa conexão no MySQL.
- migrations executadas com sucesso.
- servidor rodando em `0.0.0.0:8000`.

## 3) Verificações básicas

### 3.1 Health check
```bash
curl -i http://localhost:8000/health
```
Esperado: `HTTP/1.1 200`.

### 3.2 Documentação da API
- Swagger: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`

## 4) Testes automatizados no ambiente Docker

### 4.1 Rodar suíte completa
```bash
docker compose exec backend pytest
```

### 4.2 Rodar apenas testes de pedidos
```bash
docker compose exec backend pytest tests/integration/test_orders_api.py
```

### 4.3 Rodar teste específico da rota de status
```bash
docker compose exec backend pytest tests/integration/test_orders_api.py -k patch_order_status_route_with_id_param_alias
```

### 4.4 Gerar OpenAPI
```bash
 docker compose exec backend python manage.py spectacular --file openapi.yam
```

## 5) Smoke test ponta a ponta (manual)

> A API exige autenticação. O fluxo abaixo cria usuário admin, autentica, cria customer, produto, pedido e altera status.

### 5.1 Criar usuário (register)
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin1",
    "email": "admin1@test.com",
    "password": "Admin@123",
    "password_confirm": "Admin@123"
  }'
```

### 5.2 Obter token JWT
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/jwt/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin1","password":"Admin@123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access'])")

echo "$TOKEN" | cut -c1-30
```

### 5.3 Criar cliente
```bash
CUSTOMER_ID=$(curl -s -X POST http://localhost:8000/api/v1/customers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Cliente Smoke",
    "cpf_cnpj":"99911122233",
    "email":"cliente.smoke@test.com",
    "phone":"11999999999",
    "address":"Rua Teste, 100",
    "is_active": true
  }' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "$CUSTOMER_ID"
```

### 5.4 Criar produto
```bash
PRODUCT_ID=$(curl -s -X POST http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sku":"SMOKE-SKU-001",
    "name":"Produto Smoke",
    "description":"Produto para validação e2e",
    "price":"19.90",
    "stock_qty": 50,
    "is_active": true
  }' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "$PRODUCT_ID"
```

### 5.5 Criar pedido
```bash
ORDER_ID=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": $CUSTOMER_ID,
    \"idempotency_key\": \"smoke-order-001\",
    \"observations\": \"pedido smoke\",
    \"items\": [{\"product_id\": $PRODUCT_ID, \"qty\": 2}]
  }" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "$ORDER_ID"
```

### 5.6 Alterar status do pedido (rota requerida)
```bash
curl -i -X PATCH "http://localhost:8000/api/v1/orders/$ORDER_ID/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"CONFIRMADO","note":"aprovado no smoke test"}'
```
Esperado: `HTTP/1.1 200` e `"status":"CONFIRMADO"` no body.

## 6) Comandos de apoio

### Reiniciar somente backend
```bash
docker compose restart backend
```

### Derrubar ambiente
```bash
docker compose down
```

### Derrubar ambiente removendo volumes (reset total do banco)
```bash
docker compose down -v
```

## 7) Troubleshooting rápido

### Erro de porta em uso
- Ajuste as portas publicadas no `docker-compose.yml` ou encerre o processo que ocupa as portas.

### Backend sobe mas API falha no início
- Verifique logs: `docker compose logs -f backend`.
- Confirme se MySQL ficou saudável: `docker compose ps`.

### `401 Unauthorized`
- Token expirado ou inválido: refaça o login JWT.
- Confirme header: `Authorization: Bearer <token>`.

### `403 Forbidden`
- Usuário autenticado sem perfil/grupo permitido para a operação.
- Use usuário com privilégios adequados (`admin`, `manager` ou `operator`, conforme endpoint).
