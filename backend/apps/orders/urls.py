from django.urls import path
from .views import (
    OrderCreateView,
    OrderListView,
    OrderDetailView,
    OrderStatusPatchView,
    OrderCancelView,
)

urlpatterns = [
    path('orders', OrderCreateView.as_view()),
    path('orders/list', OrderListView.as_view()),
    path('orders/<int:pk>', OrderDetailView.as_view()),
    path('orders/<int:pk>/status', OrderStatusPatchView.as_view()),
    path('orders/<int:pk>/cancel', OrderCancelView.as_view()),
]
