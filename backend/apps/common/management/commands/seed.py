from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction

from apps.customers.models import Customer
from apps.products.models import Product
from apps.orders.services.order_service import OrderService


class Command(BaseCommand):
    help = "Seed inicial de dados"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding...")

        # ---------- GRUPOS ----------
        groups = ["admin", "manager", "operator", "viewer"]
        for g in groups:
            Group.objects.get_or_create(name=g)

        # ---------- USUÁRIOS ----------
        users_data = [
            ("admin", "admin123", "admin"),
            ("manager", "manager123", "manager"),
            ("operator", "operator123", "operator"),
            ("viewer", "viewer123", "viewer"),
        ]

        for username, password, group_name in users_data:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.is_staff = True
                user.save()

            group = Group.objects.get(name=group_name)
            user.groups.add(group)

        self.stdout.write(self.style.SUCCESS("Usuários criados."))

        # ---------- CLIENTES ----------
        customers = [
            ("Cliente A", "111", "a@test.com"),
            ("Cliente B", "222", "b@test.com"),
        ]

        customer_objs = []
        for name, doc, email in customers:
            obj, _ = Customer.objects.get_or_create(
                cpf_cnpj=doc,
                defaults={"name": name, "email": email},
            )
            customer_objs.append(obj)

        self.stdout.write(self.style.SUCCESS("Clientes criados."))

        # ---------- PRODUTOS ----------
        products_data = [
            ("SKU1", "Produto 1", "10.00", 50),
            ("SKU2", "Produto 2", "15.00", 50),
            ("SKU3", "Produto 3", "20.00", 50),
            ("SKU4", "Produto 4", "25.00", 50),
            ("SKU5", "Produto 5", "30.00", 50),
        ]

        product_objs = []
        for sku, name, price, stock in products_data:
            obj, _ = Product.objects.get_or_create(
                sku=sku,
                defaults={"name": name, "price": price, "stock_qty": stock},
            )
            product_objs.append(obj)

        self.stdout.write(self.style.SUCCESS("Produtos criados."))

        # ---------- PEDIDOS ----------
        operator = User.objects.get(username="operator")

        def create_order(customer, product, key):
            try:
                OrderService.create_order(
                    user=operator,
                    customer_id=customer.id,
                    idempotency_key=key,
                    items=[{"product_id": product.id, "qty": 1}],
                )
            except Exception:
                pass  # evita falha se já existir

        create_order(customer_objs[0], product_objs[0], "seed-1")
        create_order(customer_objs[0], product_objs[1], "seed-2")
        create_order(customer_objs[1], product_objs[2], "seed-3")

        self.stdout.write(self.style.SUCCESS("Pedidos criados."))
        self.stdout.write(self.style.SUCCESS("Seed concluído."))
