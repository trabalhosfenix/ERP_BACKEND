

# **ERP Backend — Gestão de Pedidos**

API REST para operações de ERP (**clientes, produtos, pedidos e autenticação**), construída com **Django REST Framework**, com foco em:

* Consistência transacional  
* Idempotência de requisições  
* Controle de permissões por perfil  
* Concorrência segura de estoque  
* Testes automatizados e CI

Este projeto foi pensado para uso real em ambientes multiusuário onde **duplicidade de pedidos, inconsistência de estoque e falhas de concorrência não são aceitáveis**.

---

## **O que este projeto resolve**

De forma simples:

* Cadastrar clientes e produtos  
* Criar pedidos sem duplicação acidental  
* Controlar estoque de forma segura  
* Alterar status de pedidos com regras claras  
* Permitir diferentes níveis de acesso (admin, operador, etc.)  
* Rodar tudo em Docker com testes automatizados

---

## **Stack Tecnológica**

| Camada | Tecnologia |
| ----- | ----- |
| Linguagem | Python 3.12 |
| Framework | Django \+ Django REST Framework |
| Banco | MySQL 8 (produção) / SQLite (testes locais) |
| Cache / Rate Limit | Redis 7 |
| Containerização | Docker / Docker Compose |
| Testes | Pytest |
| Documentação | OpenAPI / Swagger (`/docs`) \+ Redoc (`/redoc`) |
| CI | GitHub Actions |

---

## **Funcionalidades Principais**

### **Autenticação e Usuários**

* JWT e sessão  
* Cadastro e gestão de usuários  
* Perfis de acesso via grupos Django

### **Clientes**

* Cadastro  
* Consulta  
* Soft delete

### **Produtos**

* Cadastro  
* Consulta  
* Atualização de estoque  
* SKU único

### **Pedidos**

* Criação idempotente  
* Consulta e detalhamento  
* Cancelamento com reversão de estoque  
* Transição de status com máquina de estados  
* Histórico de status  
* Eventos de domínio

### **Infraestrutura Comum**

* Soft delete  
* Paginação  
* Rate limit por IP  
* Health check  
* Permissões por perfil

---

## **Endpoints da API (v1)**

**Base:** `/api/v1`

### **Health e Docs**

* `GET /health`  
* `GET /docs`  
* `GET /redoc`  
* `GET /api/schema`

### **Autenticação**

* `POST /auth/register`  
* `POST /auth/jwt/login`  
* `POST /auth/jwt/refresh`  
* `POST /auth/session/login`  
* `POST /auth/session/logout`  
* `GET /auth/me`

### **Clientes**

* `POST /customers`  
* `GET /customers`  
* `GET /customers/:id`

### **Produtos**

* `POST /products`  
* `GET /products`  
* `PATCH /products/:id/stock`

### **Pedidos**

* `POST /orders`  
* `GET /orders`  
* `GET /orders/:id`  
* `PATCH /orders/:id/status`  
* `DELETE /orders/:id`

---

## **Regras de Negócio Importantes**

### **Idempotência de Pedido**

Evita duplicidade quando o cliente envia a mesma requisição duas vezes.

Chave única:

`(customer_id + idempotency_key)`

### **Controle de Estoque**

* Transação atômica  
* Lock pessimista (`select_for_update`)  
* Concorrência segura

### **Cancelamento**

* Permitido apenas em `PENDENTE` ou `CONFIRMADO`  
* Devolve estoque automaticamente

---

## **Fluxo de Status do Pedido**

`PENDENTE → CONFIRMADO → SEPARADO → ENVIADO → ENTREGUE`  
          `↘ CANCELADO`

`ENTREGUE` e `CANCELADO` são estados finais.

---

## **Permissões por Perfil**

Perfis baseados em **Grupos do Django**:

| Ação | Perfis |
| ----- | ----- |
| Leitura | Todos |
| Criar Cliente/Produto | Admin, Manager |
| Criar Pedido | Admin, Manager, Operator |
| Alterar Status | Admin, Manager, Operator |
| Cancelar Pedido | Admin, Manager |
| Gestão de Usuários | Admin, Manager |
| Superuser | Acesso total |

---

## **Executando Localmente (Docker)**

`cp .env.example .env`  
`docker compose up --build`

URLs:

* API → [http://localhost:8000](http://localhost:8000)  
* Swagger → [http://localhost:8000/docs](http://localhost:8000/docs)  
* Redoc → [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## **Rodando Testes**

### **Com SQLite (rápido)**

`DB_ENGINE=sqlite pytest`

### **Com Docker (ambiente real)**

`docker compose exec backend pytest`

---

## **Integração Contínua (CI)**

O projeto utiliza **GitHub Actions** para:

* Build automático  
* Execução de migrations  
* Execução da suíte de testes  
* Validação de pull requests  
* Prevenção de regressões

---

## **Estrutura de Pastas**

`backend/apps/authentication  → usuários e login`  
`backend/apps/customers       → clientes`  
`backend/apps/products        → produtos`  
`backend/apps/orders          → pedidos e regras de negócio`  
`backend/apps/common          → componentes compartilhados`  
`backend/config               → settings Django`  
`tests/                       → testes unitários e integração`  
`frontend/                    → interface simples de apoio`

---

## **Decisões Arquiteturais**

Detalhamento técnico completo em:

`ARCHITECTURE.md`

---

## **Guia Operacional Docker**

Para smoke tests e fluxo completo:

`docs/GUIA_DOCKER_TESTES.md`

---

## **Para Quem é Este Projeto**

* Desenvolvedores backend  
* Estudantes de arquitetura REST  
* Times que precisam de referência de ERP simples  
* Demonstração de boas práticas com Django \+ Docker \+ CI

---

### **Resumo Técnico**

Este backend demonstra:

* Arquitetura em camadas  
* Idempotência forte  
* Controle de concorrência  
* Máquina de estados  
* Testes automatizados  
* CI/CD preparado  
* Boas práticas de API REST

