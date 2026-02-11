from rest_framework import generics, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product
from .serializers import ProductCreateSerializer, ProductDetailSerializer, ProductStockPatchSerializer

class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductCreateSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['sku', 'name', 'description']
    ordering_fields = ['created_at', 'name', 'price', 'stock_qty']
    ordering = ['-created_at']

class ProductStockUpdateView(APIView):
    def patch(self, request, pk: int):
        product = generics.get_object_or_404(Product, pk=pk)

        ser = ProductStockPatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        product.stock_qty = ser.validated_data['stock_qty']
        product.save(update_fields=['stock_qty', 'updated_at'])

        return Response(ProductDetailSerializer(product).data, status=status.HTTP_200_OK)
