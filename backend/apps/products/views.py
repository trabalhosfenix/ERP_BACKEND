from django.db import transaction
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product
from .serializers import ProductCreateSerializer, ProductDetailSerializer, ProductStockPatchSerializer


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductCreateSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["sku", "name", "description"]
    ordering_fields = ["created_at", "name", "price", "stock_qty"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Product.objects.all()
        is_active = self.request.query_params.get("is_active")
        if is_active in ["true", "false"]:
            queryset = queryset.filter(is_active=is_active == "true")
        return queryset


class ProductStockUpdateView(APIView):
    @transaction.atomic
    def patch(self, request, pk: int):
        product = generics.get_object_or_404(Product.objects.select_for_update(), pk=pk)
        serializer = ProductStockPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product.stock_qty = serializer.validated_data["stock_qty"]
        product.save(update_fields=["stock_qty", "updated_at"])
        return Response(ProductDetailSerializer(product).data, status=status.HTTP_200_OK)
