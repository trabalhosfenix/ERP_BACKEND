# Architecture

## Padrões adotados
- **Controller -> Service -> Model/Repository implícito**: views DRF delegam regras de negócio para `OrderService`.
- **SRP/SOLID**: validações e transações críticas no serviço, serializers só cuidam de DTO/validação de contrato.
- **Domain events**: mudança de status publica evento de domínio (`ORDER_STATUS_CHANGED`) e registra consumo.

## Fluxo de criação de pedido
1. Controller valida payload com serializer.
2. `OrderService.create_order` valida cliente e itens.
3. Lock pessimista de produtos (`select_for_update`) dentro de transação ACID.
4. Reserva de estoque, criação de `Order` e `OrderItem`.
5. Histórico inicial de status.
6. Persistência de idempotência em Redis para retries.

## Fluxo de status
- `OrderService.change_status` valida transição por matriz (`can_transition`).
- Salva histórico e emite domain event.

## Trade-offs
- Idempotência reforçada por dupla proteção (constraint no MySQL + cache Redis).
- Consumer de domain event síncrono simplifica teste/local dev; em produção poderia ser assíncrono (worker dedicado).
- Soft delete aplicado em modelos críticos para retenção e auditabilidade.
