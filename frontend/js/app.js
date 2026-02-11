const app = {
  apiBaseUrl: "http://localhost:8000/api/v1", // Altere para a URL da sua API
  authToken: null,
  currentTab: "produtos",
  pagination: {
    produtos: { offset: 0, limit: 10, count: 0 },
    pedidos: { offset: 0, limit: 10, count: 0 },
    clientes: { offset: 0, limit: 10, count: 0 },
  },

  init() {
    this.loadCustomers();
    this.loadProducts();
    this.loadOrders();
    this.setupEventListeners();
  },

  setupEventListeners() {
    // Formulários
    document.getElementById("productForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this.saveProduct();
    });

    document.getElementById("stockForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this.updateStock();
    });

    document.getElementById("customerForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this.saveCustomer();
    });

    document.getElementById("orderForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this.createOrder();
    });

    document.getElementById("statusForm").addEventListener("submit", (e) => {
      e.preventDefault();
      this.updateOrderStatus();
    });

    // Buscas
    document
      .getElementById("productSearch")
      .addEventListener("keypress", (e) => {
        if (e.key === "Enter") this.loadProducts();
      });

    document.getElementById("orderSearch").addEventListener("keypress", (e) => {
      if (e.key === "Enter") this.loadOrders();
    });

    document
      .getElementById("customerSearch")
      .addEventListener("keypress", (e) => {
        if (e.key === "Enter") this.loadCustomers();
      });
  },

  showTab(tabName) {
    this.currentTab = tabName;
    document
      .querySelectorAll(".tab-content")
      .forEach((el) => el.classList.remove("active"));
    document.getElementById(tabName).classList.add("active");

    document
      .querySelectorAll(".tab-button")
      .forEach((el) => el.classList.remove("active"));
    event.target.classList.add("active");

    // Recarrega dados da aba
    switch (tabName) {
      case "produtos":
        this.loadProducts();
        break;
      case "pedidos":
        this.loadOrders();
        break;
      case "clientes":
        this.loadCustomers();
        break;
    }
  },

  // Autenticação
  async login() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    this.authToken = btoa(`${username}:${password}`);
    this.init();

    document.querySelector(".auth-section").style.display = "none";
    this.showNotification("Login realizado com sucesso!", "success");
  },

  // Requisições HTTP
  async request(endpoint, options = {}) {
    const base = String(this.apiBaseUrl || "").replace(/\/+$/, "");

    let ep = String(endpoint || "");
    if (!ep.startsWith("/")) ep = "/" + ep;

    // separa path e query
    const [rawPath, rawQuery = ""] = ep.split("?");
    // remove trailing slashes do PATH (mantém "/customers/1" ok, remove "/customers/")
    const path = rawPath.replace(/\/+$/, "");
    const url = rawQuery ? `${base}${path}?${rawQuery}` : `${base}${path}`;

    console.log("[API]", url); // debug obrigatório agora

    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    if (this.authToken) headers["Authorization"] = `Basic ${this.authToken}`;

    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    if (response.status === 204) return null;
    return await response.json();
  },

  // Produtos
  async loadProducts() {
    const search = document.getElementById("productSearch").value;
    const { limit, offset } = this.pagination.produtos;

    let url = `/products/?limit=${limit}&offset=${offset}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    try {
      const data = await this.request(url);
      this.pagination.produtos.count = data.count;
      this.renderProducts(data.results);
      this.renderPagination(
        "productsPagination",
        this.pagination.produtos,
        "loadProducts",
      );
    } catch (error) {
      console.error("Erro ao carregar produtos:", error);
    }
  },

  renderProducts(products) {
    const tbody = document.getElementById("productsTableBody");
    tbody.innerHTML = "";

    products.forEach((product) => {
      const row = tbody.insertRow();
      row.innerHTML = `
                <td>${product.id}</td>
                <td>${product.sku}</td>
                <td>${product.name}</td>
                <td>R$ ${parseFloat(product.price).toFixed(2)}</td>
                <td>${product.stock_qty || 0}</td>
                <td><span class="status-badge ${product.is_active ? "status-ATIVO" : "status-INATIVO"}">${product.is_active ? "Ativo" : "Inativo"}</span></td>
                <td>
                    <div class="action-buttons">
                        <button onclick="app.showStockModal(${product.id})" class="btn btn-secondary btn-small">📦 Estoque</button>
                    </div>
                </td>
            `;
    });
  },

  async saveProduct() {
    const productData = {
      sku: document.getElementById("productSku").value,
      name: document.getElementById("productName").value,
      description: document.getElementById("productDescription").value,
      price: document.getElementById("productPrice").value,
      stock_qty: parseInt(document.getElementById("productStock").value),
      is_active: document.getElementById("productActive").checked,
    };

    const productId = document.getElementById("productId").value;

    try {
      if (productId) {
        await this.request(`/products/${productId}/`, {
          method: "PUT",
          body: JSON.stringify(productData),
        });
        this.showNotification("Produto atualizado com sucesso!", "success");
      } else {
        await this.request("/products/", {
          method: "POST",
          body: JSON.stringify(productData),
        });
        this.showNotification("Produto criado com sucesso!", "success");
      }

      this.closeProductModal();
      this.loadProducts();
    } catch (error) {
      console.error("Erro ao salvar produto:", error);
      this.showNotification("Erro ao salvar produto!", "error");
    }
  },

  showProductModal(productId = null) {
    document.getElementById("productModalTitle").textContent = productId
      ? "Editar Produto"
      : "Novo Produto";
    document.getElementById("productId").value = productId || "";

    if (productId) {
      this.loadProductDetails(productId);
    } else {
      document.getElementById("productForm").reset();
    }

    document.getElementById("productModal").style.display = "block";
  },

  closeProductModal() {
    document.getElementById("productModal").style.display = "none";
    document.getElementById("productForm").reset();
  },

  showStockModal(productId) {
    document.getElementById("stockProductId").value = productId;
    document.getElementById("stockQty").value = "";
    document.getElementById("stockModal").style.display = "block";
  },

  closeStockModal() {
    document.getElementById("stockModal").style.display = "none";
  },

  async updateStock() {
    const productId = document.getElementById("stockProductId").value;
    const stockQty = parseInt(document.getElementById("stockQty").value);

    try {
      await this.request(`/products/${productId}/stock/`, {
        method: "PATCH",
        body: JSON.stringify({ stock_qty: stockQty }),
      });

      this.showNotification("Estoque atualizado com sucesso!", "success");
      this.closeStockModal();
      this.loadProducts();
    } catch (error) {
      console.error("Erro ao atualizar estoque:", error);
      this.showNotification("Erro ao atualizar estoque!", "error");
    }
  },

  // Clientes
  async loadCustomers() {
    const search = document.getElementById("customerSearch").value;
    const { limit, offset } = this.pagination.clientes;

    let url = `/customers/?limit=${limit}&offset=${offset}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    try {
      const data = await this.request(url);
      this.pagination.clientes.count = data.count;
      this.renderCustomers(data.results);
      this.renderPagination(
        "customersPagination",
        this.pagination.clientes,
        "loadCustomers",
      );

      // Atualiza select de clientes nos pedidos
      this.loadCustomerSelect();
    } catch (error) {
      console.error("Erro ao carregar clientes:", error);
    }
  },

  renderCustomers(customers) {
    const tbody = document.getElementById("customersTableBody");
    tbody.innerHTML = "";

    customers.forEach((customer) => {
      const row = tbody.insertRow();
      row.innerHTML = `
                <td>${customer.id}</td>
                <td>${customer.name}</td>
                <td>${customer.cpf_cnpj}</td>
                <td>${customer.email}</td>
                <td>${customer.phone || "-"}</td>
                <td><span class="status-badge ${customer.is_active ? "status-ATIVO" : "status-INATIVO"}">${customer.is_active ? "Ativo" : "Inativo"}</span></td>
                <td>
                    <div class="action-buttons">
                        <button onclick="app.showCustomerModal(${customer.id})" class="btn btn-primary btn-small">✏️ Editar</button>
                    </div>
                </td>
            `;
    });
  },

  async saveCustomer() {
    const customerData = {
      name: document.getElementById("customerName").value,
      cpf_cnpj: document.getElementById("customerCpfCnpj").value,
      email: document.getElementById("customerEmail").value,
      phone: document.getElementById("customerPhone").value,
      address: document.getElementById("customerAddress").value,
      is_active: document.getElementById("customerActive").checked,
    };

    try {
      await this.request("/customers/", {
        method: "POST",
        body: JSON.stringify(customerData),
      });

      this.showNotification("Cliente criado com sucesso!", "success");
      this.closeCustomerModal();
      this.loadCustomers();
    } catch (error) {
      console.error("Erro ao salvar cliente:", error);
      this.showNotification("Erro ao salvar cliente!", "error");
    }
  },

  showCustomerModal(customerId = null) {
    if (customerId) {
      this.loadCustomerDetails(customerId);
    } else {
      document.getElementById("customerForm").reset();
      document.getElementById("customerActive").checked = true;
    }

    document.getElementById("customerModal").style.display = "block";
  },

  closeCustomerModal() {
    document.getElementById("customerModal").style.display = "none";
    document.getElementById("customerForm").reset();
  },

  async loadCustomerSelect() {
    try {
      const data = await this.request("/customers/?limit=100");
      const selects = document.querySelectorAll(
        ".product-select, #orderCustomer",
      );

      selects.forEach((select) => {
        if (select.id === "orderCustomer") {
          select.innerHTML = '<option value="">Selecione um cliente</option>';
        }

        data.results.forEach((customer) => {
          if (customer.is_active) {
            const option = document.createElement("option");
            option.value = customer.id;
            option.textContent = `${customer.name} - ${customer.cpf_cnpj}`;
            select.appendChild(option);
          }
        });
      });
    } catch (error) {
      console.error("Erro ao carregar clientes para select:", error);
    }
  },

  // Pedidos
  async loadOrders() {
    const search = document.getElementById("orderSearch").value;
    const { limit, offset } = this.pagination.pedidos;

    let url = `/orders/?limit=${limit}&offset=${offset}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    try {
      const data = await this.request(url);
      this.pagination.pedidos.count = data.count;
      this.renderOrders(data.results);
      this.renderPagination(
        "ordersPagination",
        this.pagination.pedidos,
        "loadOrders",
      );
    } catch (error) {
      console.error("Erro ao carregar pedidos:", error);
    }
  },

  async renderOrders(orders) {
    const tbody = document.getElementById("ordersTableBody");
    tbody.innerHTML = "";

    for (const order of orders) {
      // Carrega dados do cliente
      let customerName = "Cliente não encontrado";
      try {
        const customer = await this.request(`/customers/${order.customer_id}/`);
        customerName = customer.name;
      } catch (error) {
        console.error("Erro ao carregar cliente:", error);
      }

      const row = tbody.insertRow();
      row.innerHTML = `
                <td>${order.id}</td>
                <td>${order.number}</td>
                <td>${customerName}</td>
                <td>${new Date(order.created_at).toLocaleDateString("pt-BR")}</td>
                <td>R$ ${parseFloat(order.total).toFixed(2)}</td>
                <td><span class="status-badge status-${order.status}">${order.status}</span></td>
                <td>
                    <div class="action-buttons">
                        <button onclick="app.showStatusModal(${order.id})" class="btn btn-secondary btn-small">🔄 Status</button>
                        <button onclick="app.deleteOrder(${order.id})" class="btn btn-danger btn-small">🗑️</button>
                    </div>
                </td>
            `;
    }
  },

  showOrderModal() {
    this.loadCustomerSelect();
    this.loadProductSelect();
    document.getElementById("orderModal").style.display = "block";
  },

  closeOrderModal() {
    document.getElementById("orderModal").style.display = "none";
    document.getElementById("orderForm").reset();
    document.getElementById("orderItems").innerHTML = `
            <div class="order-item">
                <select class="product-select" required>
                    <option value="">Selecione um produto</option>
                </select>
                <input type="number" class="item-qty" min="1" placeholder="Quantidade" required>
                <button type="button" onclick="app.removeOrderItem(this)" class="btn btn-danger btn-small">Remover</button>
            </div>
        `;
  },

  async loadProductSelect() {
    try {
      const data = await this.request("/products/?limit=100");
      const selects = document.querySelectorAll(".product-select");

      selects.forEach((select) => {
        select.innerHTML = '<option value="">Selecione um produto</option>';
        data.results.forEach((product) => {
          if (product.is_active && product.stock_qty > 0) {
            const option = document.createElement("option");
            option.value = product.id;
            option.textContent = `${product.name} - SKU: ${product.sku} - Estoque: ${product.stock_qty}`;
            select.appendChild(option);
          }
        });
      });
    } catch (error) {
      console.error("Erro ao carregar produtos para select:", error);
    }
  },

  addOrderItem() {
    const itemsDiv = document.getElementById("orderItems");
    const newItem = document.createElement("div");
    newItem.className = "order-item";
    newItem.innerHTML = `
            <select class="product-select" required>
                <option value="">Selecione um produto</option>
            </select>
            <input type="number" class="item-qty" min="1" placeholder="Quantidade" required>
            <button type="button" onclick="app.removeOrderItem(this)" class="btn btn-danger btn-small">Remover</button>
        `;
    itemsDiv.appendChild(newItem);
    this.loadProductSelect();
  },

  removeOrderItem(button) {
    const itemsDiv = document.getElementById("orderItems");
    if (itemsDiv.children.length > 1) {
      button.parentElement.remove();
    } else {
      this.showNotification("O pedido deve ter pelo menos um item!", "warning");
    }
  },

  async createOrder() {
    const customerId = document.getElementById("orderCustomer").value;
    const observations = document.getElementById("orderObservations").value;
    const idempotencyKey = `order_${Date.now()}`;

    const items = [];
    const orderItems = document.querySelectorAll(".order-item");

    for (const item of orderItems) {
      const productSelect = item.querySelector(".product-select");
      const qtyInput = item.querySelector(".item-qty");

      if (productSelect.value && qtyInput.value) {
        items.push({
          product_id: parseInt(productSelect.value),
          qty: parseInt(qtyInput.value),
        });
      }
    }

    if (items.length === 0) {
      this.showNotification(
        "Adicione pelo menos um item ao pedido!",
        "warning",
      );
      return;
    }

    const orderData = {
      customer_id: parseInt(customerId),
      idempotency_key: idempotencyKey,
      observations: observations,
      items: items,
    };

    try {
      await this.request("/orders/", {
        method: "POST",
        body: JSON.stringify(orderData),
      });

      this.showNotification("Pedido criado com sucesso!", "success");
      this.closeOrderModal();
      this.loadOrders();
    } catch (error) {
      console.error("Erro ao criar pedido:", error);
      this.showNotification("Erro ao criar pedido!", "error");
    }
  },

  showStatusModal(orderId) {
    document.getElementById("statusOrderId").value = orderId;
    document.getElementById("orderStatus").value = "";
    document.getElementById("statusNote").value = "";
    document.getElementById("statusModal").style.display = "block";
  },

  closeStatusModal() {
    document.getElementById("statusModal").style.display = "none";
    document.getElementById("statusForm").reset();
  },

  async updateOrderStatus() {
    const orderId = document.getElementById("statusOrderId").value;
    const status = document.getElementById("orderStatus").value;
    const note = document.getElementById("statusNote").value;

    try {
      await this.request(`/orders/${orderId}/status/`, {
        method: "PATCH",
        body: JSON.stringify({ status, note }),
      });

      this.showNotification("Status do pedido atualizado!", "success");
      this.closeStatusModal();
      this.loadOrders();
    } catch (error) {
      console.error("Erro ao atualizar status:", error);
      this.showNotification("Erro ao atualizar status!", "error");
    }
  },

  async deleteOrder(orderId) {
    if (confirm("Tem certeza que deseja excluir este pedido?")) {
      try {
        await this.request(`/orders/${orderId}/`, {
          method: "DELETE",
        });

        this.showNotification("Pedido excluído com sucesso!", "success");
        this.loadOrders();
      } catch (error) {
        console.error("Erro ao excluir pedido:", error);
        this.showNotification("Erro ao excluir pedido!", "error");
      }
    }
  },

  // Utilidades
  renderPagination(containerId, paginationData, loadFunction) {
    const container = document.getElementById(containerId);
    const totalPages = Math.ceil(paginationData.count / paginationData.limit);
    const currentPage =
      Math.floor(paginationData.offset / paginationData.limit) + 1;

    container.innerHTML = "";

    if (totalPages <= 1) return;

    // Botão Anterior
    if (currentPage > 1) {
      const prevButton = document.createElement("button");
      prevButton.textContent = "Anterior";
      prevButton.onclick = () => {
        paginationData.offset -= paginationData.limit;
        this[loadFunction]();
      };
      container.appendChild(prevButton);
    }

    // Números das páginas
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);

    for (let i = startPage; i <= endPage; i++) {
      const pageButton = document.createElement("button");
      pageButton.textContent = i;
      if (i === currentPage) {
        pageButton.classList.add("active");
      }
      pageButton.onclick = () => {
        paginationData.offset = (i - 1) * paginationData.limit;
        this[loadFunction]();
      };
      container.appendChild(pageButton);
    }

    // Botão Próximo
    if (currentPage < totalPages) {
      const nextButton = document.createElement("button");
      nextButton.textContent = "Próximo";
      nextButton.onclick = () => {
        paginationData.offset += paginationData.limit;
        this[loadFunction]();
      };
      container.appendChild(nextButton);
    }
  },

  showNotification(message, type = "info") {
    const notification = document.createElement("div");
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background-color: ${type === "success" ? "#27ae60" : type === "error" ? "#e74c3c" : "#3498db"};
            color: white;
            border-radius: 4px;
            z-index: 9999;
            animation: slideIn 0.3s ease;
        `;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.style.animation = "slideOut 0.3s ease";
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  },
};

// Inicialização
document.addEventListener("DOMContentLoaded", () => app.init());
