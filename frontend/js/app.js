const app = {
  apiBaseUrl: "http://localhost:8000/api/v1",
  authToken: localStorage.getItem("erp_jwt") || null,
  currentUser: null,

  async init() {
    if (!this.authToken) return;
    try {
      await this.loadCurrentUser();
      this.showApp();
    } catch {
      this.logout(false);
    }
  },

  get profiles() {
    return this.currentUser?.profiles || [];
  },

  hasAnyProfile(list) {
    return list.some((item) => this.profiles.includes(item));
  },

  can(action) {
    const rules = {
      view_data: ["admin", "manager", "operator", "viewer"],
      customer_create: ["admin", "manager"],
      customer_detail: ["admin", "manager", "operator", "viewer"],
      product_create: ["admin", "manager"],
      product_stock_update: ["admin", "manager", "operator"],
      order_create: ["admin", "manager", "operator"],
      order_status_update: ["admin", "manager", "operator"],
      order_cancel: ["admin", "manager"],
      user_manage: ["admin", "manager"],
    };
    return this.hasAnyProfile(rules[action] || []);
  },

  permissionSummary() {
    const all = [];
    if (this.can("view_data")) all.push("Leitura de dados");
    if (this.can("customer_create")) all.push("Criar cliente");
    if (this.can("product_create")) all.push("Criar produto");
    if (this.can("product_stock_update")) all.push("Atualizar estoque");
    if (this.can("order_create")) all.push("Criar pedido");
    if (this.can("order_status_update")) all.push("Alterar status do pedido");
    if (this.can("order_cancel")) all.push("Cancelar pedido");
    if (this.can("user_manage")) all.push("Gerenciar usuários");
    return all.join(" • ");
  },

  async request(endpoint, options = {}) {
    const url = `${this.apiBaseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (this.authToken) headers.Authorization = `Bearer ${this.authToken}`;

    const response = await fetch(url, { ...options, headers, credentials: "include" });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const data = await response.json();
        detail = data.detail || JSON.stringify(data);
      } catch {}
      throw new Error(detail);
    }

    if (response.status === 204) return null;
    return response.json();
  },

  async login() {
    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value;

    try {
      const data = await this.request("/auth/jwt/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      this.authToken = data.access;
      localStorage.setItem("erp_jwt", this.authToken);
      await this.loadCurrentUser();
      this.showApp();
      this.notify("Login realizado com sucesso.");
    } catch (error) {
      this.notify(`Falha no login: ${error.message}`, "error");
    }
  },

  async register() {
    const payload = {
      username: document.getElementById("registerUsername").value.trim(),
      email: document.getElementById("registerEmail").value.trim(),
      password: document.getElementById("registerPassword").value,
      profile: document.getElementById("registerProfile").value,
    };

    try {
      await this.request("/auth/register", { method: "POST", body: JSON.stringify(payload) });
      this.notify("Conta criada com sucesso. Faça login.");
    } catch (error) {
      this.notify(`Falha ao criar conta: ${error.message}`, "error");
    }
  },

  async loadCurrentUser() {
    this.currentUser = await this.request("/auth/me");
    document.getElementById("currentUserLabel").textContent = `${this.currentUser.username} (${this.profiles.join(", ")})`;
  },

  async logout(showMessage = true) {
    try {
      if (this.authToken) await this.request("/auth/session/logout", { method: "POST" });
    } catch {}

    this.authToken = null;
    this.currentUser = null;
    localStorage.removeItem("erp_jwt");
    document.getElementById("appPanel").classList.add("hidden");
    document.getElementById("authPanel").classList.remove("hidden");
    document.getElementById("userBadge").classList.add("hidden");
    if (showMessage) this.notify("Logout realizado.");
  },

  showApp() {
    document.getElementById("authPanel").classList.add("hidden");
    document.getElementById("appPanel").classList.remove("hidden");
    document.getElementById("userBadge").classList.remove("hidden");

    document.getElementById("permissionHint").textContent = `Permissões ativas: ${this.permissionSummary() || "nenhuma"}.`;

    document.getElementById("btnNewProduct").classList.toggle("hidden", !this.can("product_create"));
    document.getElementById("btnNewCustomer").classList.toggle("hidden", !this.can("customer_create"));
    document.getElementById("btnNewOrder").classList.toggle("hidden", !this.can("order_create"));

    const usersTabBtn = document.querySelector('[data-tab="usuarios"]');
    usersTabBtn.classList.toggle("hidden", !this.can("user_manage"));
    document.getElementById("userCreateBox").classList.toggle("hidden", !this.can("user_manage"));

    this.loadProducts();
    this.loadCustomers();
    this.loadOrders();
    if (this.can("user_manage")) this.loadUsers();
  },

  showTab(tabName, event) {
    document.querySelectorAll(".tab-content").forEach((el) => el.classList.remove("active"));
    document.getElementById(tabName).classList.add("active");
    document.querySelectorAll(".tab-button").forEach((el) => el.classList.remove("active"));
    if (event?.target) event.target.classList.add("active");

    if (tabName === "produtos") this.loadProducts();
    if (tabName === "clientes") this.loadCustomers();
    if (tabName === "pedidos") this.loadOrders();
    if (tabName === "usuarios" && this.can("user_manage")) this.loadUsers();
  },

  // ==================== PRODUTOS ====================
  async loadProducts() {
    try {
      const data = await this.request("/products?limit=50&offset=0");
      const tbody = document.getElementById("productsTableBody");
      tbody.innerHTML = "";
      data.results.forEach((p) => {
        const row = tbody.insertRow();
        const actions = [];
        if (this.can("product_create")) {
          actions.push(`<button class="btn btn-small btn-secondary" onclick="app.openProductModal(${p.id})">Editar</button>`);
        }
        if (this.can("product_stock_update")) {
          actions.push(`<button class="btn btn-small btn-secondary" onclick="app.promptUpdateStock(${p.id}, ${p.stock_qty || 0})">Estoque</button>`);
        }
        row.innerHTML = `<td>${p.id}</td><td>${p.sku}</td><td>${p.name}</td><td>R$ ${Number(p.price).toFixed(2)}</td><td>${p.stock_qty}</td><td>${p.is_active ? "Ativo" : "Inativo"}</td><td>${actions.join("") || "-"}</td>`;
      });
    } catch (error) {
      this.notify(`Erro ao carregar produtos: ${error.message}`, "error");
    }
  },

  openProductModal(productId = null) {
    if (!this.can("product_create")) return this.notify("Sem permissão.", "error");

    const isEdit = productId !== null;
    const modal = this.createModal(isEdit ? "Editar Produto" : "Novo Produto", `
      <div class="form-group">
        <label>SKU *</label>
        <input type="text" id="modalProductSku" ${isEdit ? 'disabled' : ''} />
      </div>
      <div class="form-group">
        <label>Nome *</label>
        <input type="text" id="modalProductName" />
      </div>
      <div class="form-group">
        <label>Descrição</label>
        <textarea id="modalProductDescription"></textarea>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Preço *</label>
          <input type="number" step="0.01" id="modalProductPrice" />
        </div>
        <div class="form-group">
          <label>Estoque *</label>
          <input type="number" id="modalProductStock" />
        </div>
      </div>
      <div class="form-group">
        <label>
          <input type="checkbox" id="modalProductActive" checked /> Produto ativo
        </label>
      </div>
    `, async () => {
      const payload = {
        sku: document.getElementById("modalProductSku").value.trim(),
        name: document.getElementById("modalProductName").value.trim(),
        description: document.getElementById("modalProductDescription").value.trim(),
        price: document.getElementById("modalProductPrice").value,
        stock_qty: parseInt(document.getElementById("modalProductStock").value),
        is_active: document.getElementById("modalProductActive").checked,
      };

      if (!payload.sku || !payload.name || !payload.price) {
        return this.notify("Preencha os campos obrigatórios.", "error");
      }

      try {
        if (isEdit) {
          await this.request(`/products/${productId}`, {
            method: "PATCH",
            body: JSON.stringify(payload),
          });
          this.notify("Produto atualizado com sucesso.");
        } else {
          await this.request("/products", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          this.notify("Produto criado com sucesso.");
        }
        this.closeModal();
        this.loadProducts();
      } catch (error) {
        this.notify(`Erro: ${error.message}`, "error");
      }
    });

    if (isEdit) {
      this.request(`/products/${productId}`).then(product => {
        document.getElementById("modalProductSku").value = product.sku;
        document.getElementById("modalProductName").value = product.name;
        document.getElementById("modalProductDescription").value = product.description || "";
        document.getElementById("modalProductPrice").value = product.price;
        document.getElementById("modalProductStock").value = product.stock_qty;
        document.getElementById("modalProductActive").checked = product.is_active;
      });
    }
  },

  async promptUpdateStock(productId, currentQty) {
    if (!this.can("product_stock_update")) return this.notify("Sem permissão para atualizar estoque.", "error");
    
    const { value: qty } = await Swal.fire({
      title: `Atualizar Estoque - Produto #${productId}`,
      html: `
        <div style="text-align: left;">
          <p style="margin-bottom: 1rem; color: #666;">Estoque atual: <strong>${currentQty} unidades</strong></p>
          <label for="swal-stock" style="display: block; width: -webkit-fill-available; margin-bottom: 0.5rem; font-weight: 500;">Nova Quantidade:</label>
          <input type="number" id="swal-stock" class="swal2-input" value="${currentQty}" min="0" style="width: -webkit-fill-available; height: auto; padding: 0.75rem;">
        </div>
      `,
      focusConfirm: false,
      showCancelButton: true,
      confirmButtonText: 'Atualizar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#667eea',
      preConfirm: () => {
        const value = parseInt(document.getElementById('swal-stock').value);
        if (isNaN(value) || value < 0) {
          Swal.showValidationMessage('Digite uma quantidade válida (número inteiro não negativo)');
          return false;
        }
        return value;
      }
    });

    if (qty === undefined) return;

    try {
      await this.request(`/products/${productId}/stock`, {
        method: "PATCH",
        body: JSON.stringify({ stock_qty: qty }),
      });
      this.notify("Estoque atualizado com sucesso.");
      this.loadProducts();
    } catch (error) {
      this.notify(`Erro: ${error.message}`, "error");
    }
  },

  // ==================== CLIENTES ====================
  async loadCustomers() {
    try {
      const data = await this.request("/customers?limit=50&offset=0");
      const tbody = document.getElementById("customersTableBody");
      tbody.innerHTML = "";
      data.results.forEach((c) => {
        const row = tbody.insertRow();
        const actions = [];
        if (this.can("customer_detail")) {
          actions.push(`<button class="btn btn-small btn-secondary" onclick="app.viewCustomer(${c.id})">Ver</button>`);
        }
        if (this.can("customer_create")) {
          actions.push(`<button class="btn btn-small btn-secondary" onclick="app.openCustomerModal(${c.id})">Editar</button>`);
        }
        row.innerHTML = `<td>${c.id}</td><td>${c.name}</td><td>${c.cpf_cnpj}</td><td>${c.email}</td><td>${c.is_active ? "Ativo" : "Inativo"}</td><td>${actions.join("") || "-"}</td>`;
      });
    } catch (error) {
      this.notify(`Erro ao carregar clientes: ${error.message}`, "error");
    }
  },

  async viewCustomer(customerId) {
    try {
      const customer = await this.request(`/customers/${customerId}`);
      const modal = this.createModal(`Cliente #${customer.id}`, `
        <div class="order-details-grid">
          <div class="detail-item">
            <label>Nome</label>
            <div class="value">${customer.name}</div>
          </div>
          <div class="detail-item">
            <label>CPF/CNPJ</label>
            <div class="value">${customer.cpf_cnpj}</div>
          </div>
          <div class="detail-item">
            <label>Email</label>
            <div class="value">${customer.email}</div>
          </div>
          <div class="detail-item">
            <label>Telefone</label>
            <div class="value">${customer.phone || "-"}</div>
          </div>
          <div class="detail-item">
            <label>Endereço</label>
            <div class="value">${customer.address || "-"}</div>
          </div>
          <div class="detail-item">
            <label>Status</label>
            <div class="value">${customer.is_active ? "Ativo" : "Inativo"}</div>
          </div>
        </div>
      `, null, "Fechar");
    } catch (error) {
      this.notify(`Erro: ${error.message}`, "error");
    }
  },

  openCustomerModal(customerId = null) {
    if (!this.can("customer_create")) return this.notify("Sem permissão.", "error");

    const isEdit = customerId !== null;
    const modal = this.createModal(isEdit ? "Editar Cliente" : "Novo Cliente", `
      <div class="form-group">
        <label>Nome *</label>
        <input type="text" id="modalCustomerName" />
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>CPF/CNPJ *</label>
          <input type="text" id="modalCustomerCpfCnpj" />
        </div>
        <div class="form-group">
          <label>Email *</label>
          <input type="email" id="modalCustomerEmail" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>Telefone</label>
          <input type="text" id="modalCustomerPhone" />
        </div>
        <div class="form-group">
          <label>Endereço</label>
          <input type="text" id="modalCustomerAddress" />
        </div>
      </div>
      <div class="form-group">
        <label>
          <input type="checkbox" id="modalCustomerActive" checked /> Cliente ativo
        </label>
      </div>
    `, async () => {
      const payload = {
        name: document.getElementById("modalCustomerName").value.trim(),
        cpf_cnpj: document.getElementById("modalCustomerCpfCnpj").value.trim(),
        email: document.getElementById("modalCustomerEmail").value.trim(),
        phone: document.getElementById("modalCustomerPhone").value.trim(),
        address: document.getElementById("modalCustomerAddress").value.trim(),
        is_active: document.getElementById("modalCustomerActive").checked,
      };

      if (!payload.name || !payload.cpf_cnpj || !payload.email) {
        return this.notify("Preencha os campos obrigatórios.", "error");
      }

      try {
        if (isEdit) {
          await this.request(`/customers/${customerId}`, {
            method: "PATCH",
            body: JSON.stringify(payload),
          });
          this.notify("Cliente atualizado com sucesso.");
        } else {
          await this.request("/customers", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          this.notify("Cliente criado com sucesso.");
        }
        this.closeModal();
        this.loadCustomers();
      } catch (error) {
        this.notify(`Erro: ${error.message}`, "error");
      }
    });

    if (isEdit) {
      this.request(`/customers/${customerId}`).then(customer => {
        document.getElementById("modalCustomerName").value = customer.name;
        document.getElementById("modalCustomerCpfCnpj").value = customer.cpf_cnpj;
        document.getElementById("modalCustomerEmail").value = customer.email;
        document.getElementById("modalCustomerPhone").value = customer.phone || "";
        document.getElementById("modalCustomerAddress").value = customer.address || "";
        document.getElementById("modalCustomerActive").checked = customer.is_active;
      });
    }
  },

  // ==================== PEDIDOS ====================
  async loadOrders() {
    try {
      const data = await this.request("/orders?limit=50&offset=0");
      const tbody = document.getElementById("ordersTableBody");
      tbody.innerHTML = "";
      data.results.forEach((o) => {
        const row = tbody.insertRow();
        const actions = [];
        actions.push(`<button class="btn btn-small btn-secondary" onclick="app.viewOrder(${o.id})">Ver</button>`);
        if (this.can("order_status_update")) {
          actions.push(`<button class="btn btn-small btn-secondary" onclick="app.promptUpdateOrderStatus(${o.id}, '${o.status}')">Status</button>`);
        }
        if (this.can("order_cancel")) {
          actions.push(`<button class="btn btn-small btn-danger" onclick="app.cancelOrder(${o.id})">Cancelar</button>`);
        }
        row.innerHTML = `<td>${o.id}</td><td>${o.number}</td><td>${o.customer_id}</td><td>R$ ${Number(o.total).toFixed(2)}</td><td>${o.status}</td><td>${actions.join("") || "-"}</td>`;
      });
    } catch (error) {
      this.notify(`Erro ao carregar pedidos: ${error.message}`, "error");
    }
  },

  async viewOrder(orderId) {
    try {
      const order = await this.request(`/orders/${orderId}`);
      
      let itemsHtml = '';
      if (order.items && order.items.length > 0) {
        itemsHtml = `
          <h4 style="margin-top: 1.5rem; margin-bottom: 0.75rem;">Itens do Pedido</h4>
          <table class="order-items-table">
            <thead>
              <tr>
                <th>Produto ID</th>
                <th>Quantidade</th>
                <th>Preço Unit.</th>
                <th>Subtotal</th>
              </tr>
            </thead>
            <tbody>
              ${order.items.map(item => `
                <tr>
                  <td>${item.product_id}</td>
                  <td>${item.qty}</td>
                  <td>R$ ${Number(item.unit_price || 0).toFixed(2)}</td>
                  <td>R$ ${Number(item.subtotal || 0).toFixed(2)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      }

      const modal = this.createModal(`Pedido #${order.number}`, `
        <div class="order-details-grid">
          <div class="detail-item">
            <label>ID</label>
            <div class="value">${order.id}</div>
          </div>
          <div class="detail-item">
            <label>Número</label>
            <div class="value">${order.number}</div>
          </div>
          <div class="detail-item">
            <label>Cliente ID</label>
            <div class="value">${order.customer_id}</div>
          </div>
          <div class="detail-item">
            <label>Status</label>
            <div class="value">${order.status}</div>
          </div>
          <div class="detail-item">
            <label>Total</label>
            <div class="value">R$ ${Number(order.total).toFixed(2)}</div>
          </div>
          <div class="detail-item">
            <label>Observações</label>
            <div class="value">${order.observations || "-"}</div>
          </div>
        </div>
        ${itemsHtml}
      `, null, "Fechar");
    } catch (error) {
      this.notify(`Erro: ${error.message}`, "error");
    }
  },

  async openOrderModal() {
    if (!this.can("order_create")) return this.notify("Sem permissão.", "error");

    // Carregar clientes e produtos
    const customers = await this.request("/customers?limit=100");
    const products = await this.request("/products?limit=100");

    if (!customers.results.length || !products.results.length) {
      return this.notify("Crie pelo menos 1 cliente e 1 produto.", "error");
    }

    const modal = this.createModal("Novo Pedido", `
      <div class="form-group">
        <label>Cliente *</label>
        <select id="modalOrderCustomer">
          ${customers.results.map(c => `<option value="${c.id}">${c.name} (${c.cpf_cnpj})</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label>Observações</label>
        <textarea id="modalOrderObservations"></textarea>
      </div>
      <div class="order-items">
        <div class="order-items-header">
          <h4>Itens do Pedido</h4>
          <button type="button" class="btn-add-item" onclick="app.addOrderItem()">+ Adicionar item</button>
        </div>
        <div id="orderItemsContainer"></div>
      </div>
    `, async () => {
      const items = [];
      document.querySelectorAll(".order-item").forEach(item => {
        const productId = item.querySelector(".item-product").value;
        const qty = parseInt(item.querySelector(".item-qty").value);
        if (productId && qty > 0) {
          items.push({ product_id: parseInt(productId), qty });
        }
      });

      if (items.length === 0) {
        return this.notify("Adicione pelo menos 1 item ao pedido.", "error");
      }

      const payload = {
        customer_id: parseInt(document.getElementById("modalOrderCustomer").value),
        idempotency_key: `order_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        observations: document.getElementById("modalOrderObservations").value.trim(),
        items,
      };

      try {
        await this.request("/orders", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        this.notify("Pedido criado com sucesso.");
        this.closeModal();
        this.loadOrders();
      } catch (error) {
        this.notify(`Erro: ${error.message}`, "error");
      }
    });

    // Armazenar produtos globalmente para usar no addOrderItem
    window._availableProducts = products.results;
    
    // Adicionar primeiro item
    this.addOrderItem();
  },

  addOrderItem() {
    const container = document.getElementById("orderItemsContainer");
    const itemDiv = document.createElement("div");
    itemDiv.className = "order-item";
    itemDiv.innerHTML = `
      <div class="form-group" style="margin: 0;">
        <select class="item-product">
          ${window._availableProducts.map(p => `<option value="${p.id}">${p.name} (SKU: ${p.sku}) - R$ ${Number(p.price).toFixed(2)}</option>`).join('')}
        </select>
      </div>
      <div class="form-group" style="margin: 0;">
        <input type="number" class="item-qty" value="1" min="1" placeholder="Quantidade" />
      </div>
      <button type="button" class="btn-remove-item" onclick="this.parentElement.remove()">Remover</button>
    `;
    container.appendChild(itemDiv);
  },

  async promptUpdateOrderStatus(orderId, currentStatus) {
    if (!this.can("order_status_update")) return this.notify("Sem permissão para alterar status.", "error");
    
    const statusOptions = {
      'PENDENTE': 'Pendente',
      'CONFIRMADO': 'Confirmado',
      'SEPARADO': 'Separado',
      'ENVIADO': 'Enviado',
      'ENTREGUE': 'Entregue',
      'CANCELADO': 'Cancelado'
    };

    const { value: formValues } = await Swal.fire({
      title: `Atualizar Status do Pedido #${orderId}`,
      html: `
        <div style="text-align: left;">
          <p style="margin-bottom: 1rem; color: #666;">Status atual: <strong>${statusOptions[currentStatus] || currentStatus}</strong></p>
          <label for="swal-status" style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Novo Status:</label>
          <select id="swal-status" class="swal2-input" style="width: 100%; padding: 0.75rem; margin-bottom: 1rem; height: auto;">
            ${Object.entries(statusOptions).map(([value, label]) => 
              `<option value="${value}" ${value === currentStatus ? 'selected' : ''}>${label}</option>`
            ).join('')}
          </select>
          <label for="swal-note" style="display: block; width: -webkit-fill-available; margin-bottom: 0.5rem; font-weight: 500;">Observação (opcional):</label>
          <textarea id="swal-note" class="swal2-textarea" placeholder="Adicione uma observação sobre a mudança de status..." style="width: -webkit-fill-available; height: 100px; min-height: 80px;"></textarea>
        </div>
      `,
      focusConfirm: false,
      showCancelButton: true,
      confirmButtonText: 'Atualizar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#667eea',
      preConfirm: () => {
        return {
          status: document.getElementById('swal-status').value,
          note: document.getElementById('swal-note').value || 'Atualização via frontend'
        }
      }
    });

    if (!formValues) return;

    try {
      await this.request(`/orders/${orderId}/status`, {
        method: "PATCH",
        body: JSON.stringify(formValues),
      });
      this.notify("Status atualizado com sucesso.");
      this.loadOrders();
    } catch (error) {
      this.notify(`Erro ao atualizar status: ${error.message}`, "error");
    }
  },

  async cancelOrder(orderId) {
    if (!this.can("order_cancel")) return this.notify("Sem permissão para cancelar pedido.", "error");
    
    const result = await Swal.fire({
      title: 'Cancelar pedido?',
      html: `Tem certeza que deseja cancelar o pedido <strong>#${orderId}</strong>?<br><small>Esta ação não pode ser desfeita.</small>`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#f56565',
      cancelButtonColor: '#718096',
      confirmButtonText: 'Sim, cancelar',
      cancelButtonText: 'Não'
    });

    if (!result.isConfirmed) return;

    try {
      await this.request(`/orders/${orderId}`, {
        method: "DELETE",
        body: JSON.stringify({ note: "Cancelado via frontend" }),
      });
      
      Swal.fire({
        title: 'Cancelado!',
        text: 'O pedido foi cancelado com sucesso.',
        icon: 'success',
        timer: 2000,
        showConfirmButton: false
      });
      
      this.loadOrders();
    } catch (error) {
      this.notify(`Erro ao cancelar pedido: ${error.message}`, "error");
    }
  },

  // ==================== USUÁRIOS ====================
  async loadUsers() {
    if (!this.can("user_manage")) return;

    try {
      const users = await this.request("/auth/users");
      const tbody = document.getElementById("usersTableBody");
      tbody.innerHTML = "";

      users.forEach((u) => {
        const row = tbody.insertRow();
        row.innerHTML = `
          <td>${u.id}</td>
          <td>${u.username}</td>
          <td>${u.email || "-"}</td>
          <td>${(u.profiles || []).join(", ")}</td>
          <td class="${u.is_active ? "status-active" : "status-inactive"}">${u.is_active ? "Sim" : "Não"}</td>
          <td>
            <button class="btn btn-small btn-secondary" onclick="app.toggleUserActive(${u.id}, ${u.is_active})">Ativar/Inativar</button>
            <button class="btn btn-small btn-primary" onclick="app.changeUserProfile(${u.id}, '${(u.profiles || ["viewer"])[0]}')">Perfil</button>
          </td>
        `;
      });
    } catch (error) {
      this.notify(`Erro ao carregar usuários: ${error.message}`, "error");
    }
  },

  async createManagedUser() {
    if (!this.can("user_manage")) return;

    const payload = {
      username: document.getElementById("newUserUsername").value.trim(),
      email: document.getElementById("newUserEmail").value.trim(),
      password: document.getElementById("newUserPassword").value,
      profile: document.getElementById("newUserProfile").value,
      is_active: true,
    };

    try {
      await this.request("/auth/users", { method: "POST", body: JSON.stringify(payload) });
      this.notify("Usuário criado com sucesso.");
      document.getElementById("newUserUsername").value = "";
      document.getElementById("newUserEmail").value = "";
      document.getElementById("newUserPassword").value = "";
      this.loadUsers();
    } catch (error) {
      this.notify(`Erro: ${error.message}`, "error");
    }
  },

  async toggleUserActive(userId, currentState) {
    if (!this.can("user_manage")) return;

    try {
      await this.request(`/auth/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !currentState }),
      });
      this.notify("Usuário atualizado com sucesso.");
      this.loadUsers();
    } catch (error) {
      this.notify(`Erro: ${error.message}`, "error");
    }
  },

  async changeUserProfile(userId, currentProfile) {
    if (!this.can("user_manage")) return;
    
    const profileOptions = {
      'admin': 'Admin - Acesso total',
      'manager': 'Manager - Gerenciamento completo',
      'operator': 'Operator - Operações do dia a dia',
      'viewer': 'Viewer - Apenas leitura'
    };

    const { value: profile } = await Swal.fire({
      title: `Alterar Perfil do Usuário #${userId}`,
      html: `
        <div style="text-align: left;">
          <p style="margin-bottom: 1rem; color: #666;">Perfil atual: <strong>${profileOptions[currentProfile] || currentProfile}</strong></p>
          <label for="swal-profile" style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Novo Perfil:</label>
          <select id="swal-profile" class="swal2-input" style="width: 100%; padding: 0.75rem; height: auto;">
            ${Object.entries(profileOptions).map(([value, label]) => 
              `<option value="${value}" ${value === currentProfile ? 'selected' : ''}>${label}</option>`
            ).join('')}
          </select>
        </div>
      `,
      focusConfirm: false,
      showCancelButton: true,
      confirmButtonText: 'Atualizar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#667eea',
      preConfirm: () => {
        return document.getElementById('swal-profile').value;
      }
    });

    if (!profile) return;

    try {
      await this.request(`/auth/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ profile }),
      });
      this.notify("Perfil atualizado com sucesso.");
      this.loadUsers();
    } catch (error) {
      this.notify(`Erro: ${error.message}`, "error");
    }
  },

  // ==================== MODAL HELPER ====================
  createModal(title, content, onSave, saveLabel = "Salvar", cancelLabel = "Cancelar") {
    // Remover modal existente se houver
    this.closeModal();

    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.id = "appModal";
    
    const hasSaveButton = onSave !== null;
    
    overlay.innerHTML = `
      <div class="modal">
        <h2>${title}</h2>
        ${content}
        <div class="modal-actions">
          <button class="btn btn-secondary" onclick="app.closeModal()">${cancelLabel}</button>
          ${hasSaveButton ? `<button class="btn btn-primary" id="modalSaveBtn">${saveLabel}</button>` : ''}
        </div>
      </div>
    `;
    
    document.body.appendChild(overlay);
    
    if (hasSaveButton) {
      document.getElementById("modalSaveBtn").onclick = onSave;
    }
    
    // Fechar ao clicar fora
    overlay.onclick = (e) => {
      if (e.target === overlay) this.closeModal();
    };

    return overlay;
  },

  closeModal() {
    const modal = document.getElementById("appModal");
    if (modal) modal.remove();
  },

  // ==================== NOTIFICAÇÕES ====================
  notify(message, type = "success") {
    const Toast = Swal.mixin({
      toast: true,
      position: 'top-end',
      showConfirmButton: false,
      timer: 3000,
      timerProgressBar: true,
      didOpen: (toast) => {
        toast.addEventListener('mouseenter', Swal.stopTimer)
        toast.addEventListener('mouseleave', Swal.resumeTimer)
      }
    });

    Toast.fire({
      icon: type === "error" ? 'error' : 'success',
      title: message
    });
  },
};

document.addEventListener("DOMContentLoaded", () => app.init());