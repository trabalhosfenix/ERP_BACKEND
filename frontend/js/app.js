const app = {
  apiBaseUrl: "http://localhost:8000/api/v1",
  authToken: localStorage.getItem("erp_jwt") || null,
  currentUser: null,

  async init() {
    if (this.authToken) {
      try {
        await this.loadCurrentUser();
        this.showApp();
      } catch {
        this.logout(false);
      }
    }
  },

  async request(endpoint, options = {}) {
    const url = `${this.apiBaseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (this.authToken) headers.Authorization = `Bearer ${this.authToken}`;

    const response = await fetch(url, { ...options, headers, credentials: "include" });
    if (!response.ok) {
      let detail = "Erro na requisição";
      try {
        const data = await response.json();
        detail = data.detail || JSON.stringify(data);
      } catch {}
      throw new Error(detail);
    }

    if (response.status === 204) return null;
    return response.json();
  },

  isAdminOrManager() {
    const profiles = this.currentUser?.profiles || [];
    return profiles.includes("admin") || profiles.includes("manager");
  },

  isOperatorPlus() {
    const profiles = this.currentUser?.profiles || [];
    return profiles.includes("admin") || profiles.includes("manager") || profiles.includes("operator");
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
      await this.request("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      this.notify("Conta criada com sucesso. Faça login.");
    } catch (error) {
      this.notify(`Falha ao criar conta: ${error.message}`, "error");
    }
  },

  async loadCurrentUser() {
    this.currentUser = await this.request("/auth/me");
    document.getElementById("currentUserLabel").textContent = `${this.currentUser.username} (${this.currentUser.profiles.join(", ")})`;
  },

  async logout(showMessage = true) {
    try {
      if (this.authToken) {
        await this.request("/auth/session/logout", { method: "POST" });
      }
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

    const canManage = this.isAdminOrManager();
    const canOperate = this.isOperatorPlus();

    document.getElementById("btnNewProduct").classList.toggle("hidden", !canManage);
    document.getElementById("btnNewCustomer").classList.toggle("hidden", !canManage);
    document.getElementById("btnNewOrder").classList.toggle("hidden", !canOperate);

    const usersTabBtn = document.querySelector('[data-tab="usuarios"]');
    usersTabBtn.classList.toggle("hidden", !canManage);
    document.getElementById("userCreateBox").classList.toggle("hidden", !canManage);

    this.loadProducts();
    this.loadCustomers();
    this.loadOrders();
    if (canManage) this.loadUsers();
  },

  showTab(tabName, event) {
    document.querySelectorAll(".tab-content").forEach((el) => el.classList.remove("active"));
    document.getElementById(tabName).classList.add("active");

    document.querySelectorAll(".tab-button").forEach((el) => el.classList.remove("active"));
    if (event?.target) event.target.classList.add("active");

    if (tabName === "produtos") this.loadProducts();
    if (tabName === "clientes") this.loadCustomers();
    if (tabName === "pedidos") this.loadOrders();
    if (tabName === "usuarios" && this.isAdminOrManager()) this.loadUsers();
  },

  async loadProducts() {
    try {
      const data = await this.request("/products?limit=20&offset=0");
      const tbody = document.getElementById("productsTableBody");
      tbody.innerHTML = "";
      data.results.forEach((p) => {
        const row = tbody.insertRow();
        row.innerHTML = `<td>${p.id}</td><td>${p.sku}</td><td>${p.name}</td><td>R$ ${Number(p.price).toFixed(2)}</td><td>${p.stock_qty}</td><td>${p.is_active ? "Ativo" : "Inativo"}</td>`;
      });
    } catch (error) {
      this.notify(`Erro ao carregar produtos: ${error.message}`, "error");
    }
  },

  async saveProduct() {
    const sku = `SKU-${Date.now()}`;
    try {
      await this.request("/products", {
        method: "POST",
        body: JSON.stringify({
          sku,
          name: `Produto ${new Date().toLocaleTimeString()}`,
          description: "Produto criado pela tela",
          price: "10.00",
          stock_qty: 20,
          is_active: true,
        }),
      });
      this.notify("Produto criado com sucesso.");
      this.loadProducts();
    } catch (error) {
      this.notify(`Erro ao criar produto: ${error.message}`, "error");
    }
  },

  async loadCustomers() {
    try {
      const data = await this.request("/customers?limit=20&offset=0");
      const tbody = document.getElementById("customersTableBody");
      tbody.innerHTML = "";
      data.results.forEach((c) => {
        const row = tbody.insertRow();
        row.innerHTML = `<td>${c.id}</td><td>${c.name}</td><td>${c.cpf_cnpj}</td><td>${c.email}</td><td>${c.is_active ? "Ativo" : "Inativo"}</td>`;
      });
    } catch (error) {
      this.notify(`Erro ao carregar clientes: ${error.message}`, "error");
    }
  },

  async saveCustomer() {
    try {
      await this.request("/customers", {
        method: "POST",
        body: JSON.stringify({
          name: `Cliente ${Date.now()}`,
          cpf_cnpj: `${Math.floor(Math.random() * 10 ** 11)}`,
          email: `cliente${Date.now()}@mail.com`,
          phone: "11999999999",
          address: "Rua Exemplo",
          is_active: true,
        }),
      });
      this.notify("Cliente criado com sucesso.");
      this.loadCustomers();
    } catch (error) {
      this.notify(`Erro ao criar cliente: ${error.message}`, "error");
    }
  },

  async loadOrders() {
    try {
      const data = await this.request("/orders?limit=20&offset=0");
      const tbody = document.getElementById("ordersTableBody");
      tbody.innerHTML = "";
      data.results.forEach((o) => {
        const row = tbody.insertRow();
        row.innerHTML = `<td>${o.id}</td><td>${o.number}</td><td>${o.customer_id}</td><td>R$ ${Number(o.total).toFixed(2)}</td><td>${o.status}</td>`;
      });
    } catch (error) {
      this.notify(`Erro ao carregar pedidos: ${error.message}`, "error");
    }
  },

  async quickCreateOrder() {
    try {
      const customers = await this.request("/customers?limit=1&offset=0");
      const products = await this.request("/products?limit=1&offset=0");
      if (!customers.results.length || !products.results.length) {
        this.notify("Crie pelo menos 1 cliente e 1 produto para gerar pedido.", "error");
        return;
      }

      await this.request("/orders", {
        method: "POST",
        body: JSON.stringify({
          customer_id: customers.results[0].id,
          idempotency_key: `quick_${Date.now()}`,
          observations: "Pedido rápido pela UI",
          items: [{ product_id: products.results[0].id, qty: 1 }],
        }),
      });
      this.notify("Pedido criado com sucesso.");
      this.loadOrders();
    } catch (error) {
      this.notify(`Erro ao criar pedido: ${error.message}`, "error");
    }
  },

  async loadUsers() {
    if (!this.isAdminOrManager()) return;

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
          <td><button class="btn btn-small btn-secondary" onclick="app.toggleUserActive(${u.id}, ${u.is_active})">Ativar/Inativar</button></td>
        `;
      });
    } catch (error) {
      this.notify(`Erro ao carregar usuários: ${error.message}`, "error");
    }
  },

  async createManagedUser() {
    if (!this.isAdminOrManager()) return;

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
      this.loadUsers();
    } catch (error) {
      this.notify(`Erro ao criar usuário: ${error.message}`, "error");
    }
  },

  async toggleUserActive(userId, currentState) {
    if (!this.isAdminOrManager()) return;

    try {
      await this.request(`/auth/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !currentState }),
      });
      this.notify("Usuário atualizado com sucesso.");
      this.loadUsers();
    } catch (error) {
      this.notify(`Erro ao atualizar usuário: ${error.message}`, "error");
    }
  },

  notify(message, type = "success") {
    const color = type === "error" ? "#dc2626" : "#2563eb";
    const el = document.createElement("div");
    el.textContent = message;
    el.style.cssText = `position:fixed;right:20px;top:20px;background:${color};color:white;padding:10px 14px;border-radius:8px;z-index:9999;`;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2600);
  },
};

document.addEventListener("DOMContentLoaded", () => app.init());
