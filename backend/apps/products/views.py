from rest_framework import generics, filters, status
from rest_framework.response import Response

from .models import Product
from .serializers import (
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductStockPatchSerializer,
)

class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductCreateSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["sku", "name", "description"]
    ordering_fields = ["created_at", "name", "price", "stock_qty"]
    ordering = ["-created_at"]


class ProductStockUpdateView(generics.GenericAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductStockPatchSerializer

    def patch(self, request, pk: int, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # exemplo típico: setar/ajustar estoque conforme seu serializer
        stock_qty = serializer.validated_data["stock_qty"]
        product.stock_qty = stock_qty
        product.save(update_fields=["stock_qty", "updated_at"])

        return Response(ProductDetailSerializer(product).data, status=status.HTTP_200_OK)
