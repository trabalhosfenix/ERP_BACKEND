# **Architecture**

## **1\) Visão geral**

A API é organizada em apps Django por domínio e segue um estilo em camadas:

* **Controller (Views DRF)**: valida contrato HTTP, serialização e respostas.

* **Service (regras de negócio)**: regras transacionais e invariantes de domínio.

* **Model (ORM Django)**: persistência, constraints, índices e relacionamentos.

* **Domain helpers**: enum de status, matriz de transição e eventos de domínio.

Fluxo principal do módulo de pedidos:  
 `View -> Serializer -> OrderService -> Models (transaction.atomic + locks) -> Events`

O projeto é executado em ambiente containerizado (Docker) e possui **Integração Contínua (CI)** via **GitHub Actions**, garantindo build e validação automática a cada alteração no repositório.

---

## **2\) Componentes por módulo**

### **`apps/orders`**

* `views.py`: endpoints de listagem, criação, detalhe/cancelamento e patch de status.

* `serializers.py`: contratos de entrada/saída para pedidos.

* `services/order_service.py`: núcleo de regra de negócio (criação, alteração de status, cancelamento).

* `domain/enums.py`: enum de status do pedido.

* `domain/transitions.py`: matriz de transições permitidas.

* `domain/events.py`: publicação/consumo de evento de mudança de status.

* `models.py`: `Order`, `OrderItem`, `OrderStatusHistory`, `OrderDomainEvent`.

### **`apps/customers`**

* CRUD parcial (list/create/retrieve) com busca e ordenação.

* Modelo com índices por documento/email e soft delete.

### **`apps/products`**

* List/create e patch de estoque.

* Modelo com SKU único e estoque inteiro não negativo.

### **`apps/authentication`**

* Registro, login JWT, refresh JWT.

* Login/logout de sessão.

* Endpoint `/auth/me` e gestão administrativa de usuários.

### **`apps/common`**

* `SoftDeleteModel` e managers para filtrar registros ativos.

* `ProfilePermission` por perfil e método HTTP.

* `DefaultPagination` (`limit/offset`, limite máximo configurável).

* `RateLimitMiddleware` por IP usando Redis.

* Health endpoint.

---

## **3\) Roteamento e contrato da API**

Rota raiz registra os domínios em `/api/v1/`.

No módulo de pedidos:

* `POST /api/v1/orders`

* `GET /api/v1/orders`

* `GET /api/v1/orders/:id`

* `PATCH /api/v1/orders/:id/status`

* `DELETE /api/v1/orders/:id`

### **Compatibilidade de parâmetro da rota de status**

Para preservar compatibilidade com contratos e testes já existentes, o backend suporta lookup por `id` mantendo o padrão documentado `:id`.

---

## **4\) Modelo de dados**

### **Entidades principais**

* **Customer**: identificação (`cpf_cnpj`, `email` únicos), atividade (`is_active`), soft delete.

* **Product**: `sku` único, preço, estoque (`stock_qty`), atividade e soft delete.

* **Order**:

  * FK para customer.

  * número único (`number`).

  * status com enum.

  * total, observações, `idempotency_key`.

  * unique constraint `(customer, idempotency_key)` para idempotência forte.

* **OrderItem**: itens com `qty`, `unit_price` e `subtotal`.

* **OrderStatusHistory**: trilha de auditoria de transição de status.

* **OrderDomainEvent**: registro de evento de domínio.

### **Índices e constraints relevantes**

* Índices em campos de consulta frequente (status, created\_at, chaves de busca).

* Constraint de unicidade para evitar duplicação de pedido por chave de idempotência.

---

## **5\) Regras transacionais e consistência**

### **Criação de pedido (`OrderService.create_order`)**

1. Valida payload de negócio.

2. Valida cliente ativo.

3. Idempotência Redis (best effort).

4. Idempotência forte no banco.

5. Lock pessimista de produtos (`select_for_update`).

6. Validação de estoque.

7. Criação de pedido \+ itens \+ baixa de estoque no mesmo `transaction.atomic`.

8. Histórico inicial.

9. Pós-commit grava chave no Redis.

### **Alteração de status (`OrderService.change_status`)**

1. Lock do pedido.

2. Validação de transição.

3. Atualização de status.

4. Registro de histórico.

5. Pós-commit publica evento.

### **Cancelamento (`OrderService.cancel_order`)**

1. Lock do pedido.

2. Validação de cancelabilidade.

3. Lock dos produtos.

4. Devolução de estoque.

5. Status `CANCELADO`.

6. Histórico \+ evento.

---

## **6\) Máquinas de estado**

Estados e transições:

* `PENDENTE -> CONFIRMADO | CANCELADO`

* `CONFIRMADO -> SEPARADO | CANCELADO`

* `SEPARADO -> ENVIADO`

* `ENVIADO -> ENTREGUE`

* `ENTREGUE -> (fim)`

* `CANCELADO -> (fim)`

Isoladas em `domain/transitions.py`, permitindo testes unitários independentes.

---

## **7\) Segurança e controle de acesso**

* Autenticação DRF (Sessão e JWT).

* Permissão global `IsAuthenticated`.

* `ProfilePermission` por método HTTP e perfil.

* Superuser com bypass de perfil.

---

## **8\) Observabilidade e resiliência**

* Logging estruturado JSON.

* Endpoint de health check.

* Rate limiting por IP (Redis) com fallback tolerante.

* Eventos publicados em pós-commit para consistência.

---

## **9\) Escalabilidade e trade-offs**

* Idempotência dupla (Redis \+ Banco).

* Locks pessimistas para evitar oversell.

* Eventos síncronos locais (evoluível para filas).

* Soft delete para auditoria e recuperação.

---

## **10\) Testabilidade**

### **Cobertura Automatizada**

A aplicação possui suíte de testes com **pytest**, separada em:

**Testes Unitários**

* Transições válidas e inválidas de status.

* Códigos de erro de negócio.

* Regras de domínio isoladas.

**Testes de Integração**

* Idempotência com múltiplos retries.

* Atomicidade com falha de estoque.

* Concorrência de reserva de estoque.

* Permissões de usuário.

* Cancelamento restaurando estoque.

* Listagem leve vs detalhe completo.

* Atualização de status via rota documentada.

### **Ambiente de Teste**

* Executado em containers Docker.

* Banco MySQL e Redis reais em ambiente isolado.

* Execução determinística via GitHub Actions.

---

## **11\) Integração Contínua (CI)**

### **GitHub Actions**

O projeto utiliza **GitHub Actions** para validação automática a cada *push* ou *pull request*.

Fluxo do CI:

1. Checkout do código.

2. Preparação do `.env` a partir de `.env.example`.

3. Build das imagens Docker.

4. Subida de MySQL e Redis.

5. Execução de migrations.

6. Execução da suíte `pytest`.

7. Coleta de logs em falhas.

8. Teardown do ambiente.

### **Benefícios do CI**

* Prevenção de regressões.

* Feedback imediato ao desenvolvedor.

* Padronização de qualidade.

* Segurança em refatorações.

* Redução de bugs em produção.

* Base para deploy automatizado.

* Documentação viva do comportamento do sistema.

---

## **12\) Documentação e Relatórios**

* **OpenAPI/Swagger** disponível para inspeção de contratos.

* Relatórios de execução de testes podem ser gerados manualmente.

* Arquivos de referência:

  * `Relatório de Execução de Testes.md`

  * `Relatório de Execução de Testes.pdf`

---

## **13\) Considerações Operacionais**

* `.env.example` versionado sem segredos.

* `.env` local ou gerado no CI.

* Segredos reais mantidos fora do repositório.

* Estrutura preparada para futura etapa de CD (Deploy automatizado).

