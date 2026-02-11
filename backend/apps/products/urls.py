from django.urls import path
from .views import ProductListCreateView, ProductStockUpdateView

urlpatterns = [
    path('products', ProductListCreateView.as_view(), name='products-list-create'),
    path('products/<int:pk>/stock', ProductStockUpdateView.as_view(), name='products-stock'),
]
