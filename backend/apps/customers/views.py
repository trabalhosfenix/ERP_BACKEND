from rest_framework import generics, filters
from .models import Customer
from .serializers import CustomerCreateSerializer, CustomerDetailSerializer

class CustomerListCreateView(generics.ListCreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerCreateSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'cpf_cnpj', 'email', 'phone']
    ordering_fields = ['created_at', 'name', 'email']
    ordering = ['-created_at']

class CustomerRetrieveView(generics.RetrieveAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerDetailSerializer
