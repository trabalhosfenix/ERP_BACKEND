from django.db import OperationalError
from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from .serializers import OrderCreateSerializer, OrderOutSerializer, OrderStatusPatchSerializer
from .services.order_service import BusinessError, CreateOrderInput, CreateOrderItemInput, OrderService


class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.prefetch_related("items", "status_history").select_related("customer").all().order_by("-created_at")
    serializer_class = OrderOutSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["number", "status", "customer__name"]
    ordering_fields = ["created_at", "total", "status", "number"]

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            order, created = OrderService.create_order(
                CreateOrderInput(
                    customer_id=data["customer_id"],
                    idempotency_key=data["idempotency_key"],
                    observations=data.get("observations", ""),
                    items=[CreateOrderItemInput(**item) for item in data["items"]],
                )
            )
        except BusinessError as exc:
            return Response({"detail": str(exc)}, status=getattr(exc, "status_code", 400))
        except OperationalError:
            return Response({"detail": "concurrent write conflict"}, status=409)

        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(OrderOutSerializer(order).data, status=code)


class OrderDetailCancelView(APIView):
    def get(self, request, pk: int):
        order = generics.get_object_or_404(Order.objects.prefetch_related("items", "status_history").select_related("customer"), pk=pk)
        return Response(OrderOutSerializer(order).data)

    def delete(self, request, pk: int):
        try:
            order = OrderService.cancel_order(
                order_id=pk,
                user=request.user if request.user.is_authenticated else None,
                note="canceled via api",
            )
        except BusinessError as exc:
            return Response({"detail": str(exc)}, status=getattr(exc, "status_code", 400))
        except OperationalError:
            return Response({"detail": "concurrent write conflict"}, status=409)
        return Response(OrderOutSerializer(order).data)


class OrderStatusPatchView(APIView):
    def patch(self, request, pk: int):
        serializer = OrderStatusPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = OrderService.change_status(
                order_id=pk,
                new_status=serializer.validated_data["status"],
                user=request.user if request.user.is_authenticated else None,
                note=serializer.validated_data.get("note", ""),
            )
        except BusinessError as exc:
            return Response({"detail": str(exc)}, status=getattr(exc, "status_code", 400))
        except OperationalError:
            return Response({"detail": "concurrent write conflict"}, status=409)
        return Response(OrderOutSerializer(order).data)

