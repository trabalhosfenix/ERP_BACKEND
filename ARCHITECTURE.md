# Architecture

## 1) Visão geral
A API é organizada em apps Django por domínio e segue um estilo em camadas:

- **Controller (Views DRF)**: valida contrato HTTP, serialização e respostas.
- **Service (regras de negócio)**: regras transacionais e invariantes de domínio.
- **Model (ORM Django)**: persistência, constraints, índices e relacionamentos.
- **Domain helpers**: enum de status, matriz de transição e eventos de domínio.

Fluxo principal do módulo de pedidos:
`View -> Serializer -> OrderService -> Models (transaction.atomic + locks) -> Events`

## 2) Componentes por módulo

### `apps/orders`
- `views.py`: endpoints de listagem, criação, detalhe/cancelamento e patch de status.
- `serializers.py`: contratos de entrada/saída para pedidos.
- `services/order_service.py`: núcleo de regra de negócio (criação, alteração de status, cancelamento).
- `domain/enums.py`: enum de status do pedido.
- `domain/transitions.py`: matriz de transições permitidas.
- `domain/events.py`: publicação/consumo de evento de mudança de status.
- `models.py`: `Order`, `OrderItem`, `OrderStatusHistory`, `OrderDomainEvent`.

### `apps/customers`
- CRUD parcial (list/create/retrieve) com busca e ordenação.
- Modelo com índices por documento/email e soft delete.

### `apps/products`
- List/create e patch de estoque.
- Modelo com SKU único e estoque inteiro não negativo.

### `apps/authentication`
- Registro, login JWT, refresh JWT.
- Login/logout de sessão.
- Endpoint `/auth/me` e gestão administrativa de usuários.

### `apps/common`
- `SoftDeleteModel` e managers para filtrar registros ativos.
- `ProfilePermission` por perfil e método HTTP.
- `DefaultPagination` (`limit/offset`, limite máximo configurável).
- `RateLimitMiddleware` por IP usando Redis.
- Health endpoint.

## 3) Roteamento e contrato da API
Rota raiz registra os domínios em `/api/v1/`.

No módulo de pedidos:
- `POST /api/v1/orders`
- `GET /api/v1/orders`
- `GET /api/v1/orders/:id`
- `PATCH /api/v1/orders/:id/status` (**alteração de status**)
- `DELETE /api/v1/orders/:id`

### Compatibilidade de parâmetro da rota de status
Para preservar compatibilidade com contratos e testes já existentes, o backend suporta a rota de status com lookup por id mantendo o padrão documentado `:id`.

## 4) Modelo de dados

### Entidades principais
- **Customer**: identificação (`cpf_cnpj`, `email` únicos), atividade (`is_active`), soft delete.
- **Product**: `sku` único, preço, estoque (`stock_qty`), atividade e soft delete.
- **Order**:
  - FK para customer.
  - número único (`number`).
  - status com enum.
  - total, observações, `idempotency_key`.
  - unique constraint `(customer, idempotency_key)` para idempotência forte.
- **OrderItem**: itens com `qty`, `unit_price` e `subtotal`.
- **OrderStatusHistory**: trilha de auditoria de transição de status.
- **OrderDomainEvent**: registro de evento de domínio.

### Índices e constraints relevantes
- Índices em campos de consulta frequente (status, created_at, chaves de busca).
- Constraint de unicidade para evitar duplicação de pedido por chave de idempotência.

## 5) Regras transacionais e consistência

### Criação de pedido (`OrderService.create_order`)
1. Valida payload de negócio (itens e quantidades).
2. Valida cliente existente e ativo.
3. Tenta idempotência por Redis (best effort).
4. Reforça idempotência por banco (fonte de verdade).
5. Obtém lock pessimista dos produtos (`select_for_update`).
6. Valida produtos ativos e estoque suficiente.
7. Cria pedido + itens + baixa estoque no mesmo `transaction.atomic`.
8. Salva histórico inicial.
9. Após commit, grava chave de idempotência no Redis.

### Alteração de status (`OrderService.change_status`)
1. Lock do pedido (`select_for_update`).
2. Validação de transição via matriz de estados.
3. Atualiza status.
4. Registra histórico.
5. Após commit, publica evento de domínio.

### Cancelamento (`OrderService.cancel_order`)
1. Lock do pedido.
2. Valida status cancelável (`PENDENTE`/`CONFIRMADO`).
3. Lock dos produtos dos itens.
4. Devolve estoque item a item.
5. Define status `CANCELADO`.
6. Registra histórico e evento.

## 6) Máquinas de estado
Estados e transições:
- `PENDENTE -> CONFIRMADO | CANCELADO`
- `CONFIRMADO -> SEPARADO | CANCELADO`
- `SEPARADO -> ENVIADO`
- `ENVIADO -> ENTREGUE`
- `ENTREGUE -> (sem transições)`
- `CANCELADO -> (sem transições)`

Essa validação fica isolada em `domain/transitions.py`, facilitando manutenção e testes.

## 7) Segurança e controle de acesso
- Autenticação padrão DRF:
  - Sessão (`SessionAuthentication`)
  - JWT (`JWTAuthentication`)
- Permissão global `IsAuthenticated`.
- `ProfilePermission` para autorização por método HTTP e perfil.
- Usuário superuser bypass de regras por perfil.

## 8) Observabilidade e resiliência
- Logging estruturado JSON no root logger.
- Endpoint de health check para liveness.
- Rate limiting por IP (Redis), com fallback tolerante a falha do Redis.
- Publicação de eventos em pós-commit para preservar consistência.

## 9) Escalabilidade e trade-offs
- **Idempotência em duas camadas**: Redis acelera retries; banco garante consistência.
- **Locks pessimistas**: reduzem risco de oversell em concorrência alta.
- **Eventos síncronos locais**: simplifica operação e testes; pode evoluir para fila assíncrona.
- **Soft delete**: favorece auditoria e recuperação lógica.

## 10) Testabilidade
- Testes de integração cobrem:
  - idempotência com múltiplos retries,
  - atomicidade com falha de estoque,
  - concorrência de reserva de estoque,
  - atualização de status via rota documentada.

O projeto também fornece OpenAPI para inspeção e testes exploratórios de contrato.
