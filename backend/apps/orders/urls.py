from django.urls import path

from .views import OrderDetailCancelView, OrderListCreateView, OrderStatusPatchView

urlpatterns = [
    path("orders", OrderListCreateView.as_view(), name="orders-list-create"),
    path("orders/<int:pk>", OrderDetailCancelView.as_view(), name="orders-detail-cancel"),
    path("orders/<int:pk>/status", OrderStatusPatchView.as_view(), name="orders-status"),
    # Alias para compatibilidade com contrato documentado `:id`.
    path(
        "orders/<int:id>/status",
        OrderStatusPatchView.as_view(lookup_url_kwarg="id"),
        name="orders-status-id",
    ),
]
