from rest_framework import filters, generics

from .models import Customer
from .serializers import CustomerCreateSerializer, CustomerDetailSerializer


class CustomerListCreateView(generics.ListCreateAPIView):
    serializer_class = CustomerCreateSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "cpf_cnpj", "email", "phone"]
    ordering_fields = ["created_at", "name", "email"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Customer.objects.all()
        is_active = self.request.query_params.get("is_active")
        if is_active in ["true", "false"]:
            queryset = queryset.filter(is_active=is_active == "true")
        return queryset


class CustomerRetrieveView(generics.RetrieveAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerDetailSerializer
