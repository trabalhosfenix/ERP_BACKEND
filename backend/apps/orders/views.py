from rest_framework import generics, status
from rest_framework.response import Response

from apps.common.permissions import ProfilePermission
from apps.orders.models import Order
from apps.orders.serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    OrderStatusPatchSerializer,
)
from apps.orders.services.order_service import (
    OrderService,
    CreateOrderInput,
    CreateOrderItemInput,
    BusinessError,
    ConflictError,
    NotFoundError,
)


class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderListSerializer
    permission_classes = [ProfilePermission]
    allowed_profiles_by_method = {
        "GET": ["admin", "manager", "operator", "viewer"],
        "POST": ["admin", "manager", "operator"],
    }

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OrderCreateSerializer
        return OrderListSerializer

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Para cumprir o contrato dos testes:
        # primeira criação => 201, retries idempotentes => 200
        existed = Order.objects.filter(
            customer_id=data["customer_id"],
            idempotency_key=data["idempotency_key"],
        ).exists()

        try:
            order = OrderService.create_order(
                CreateOrderInput(
                    customer_id=data["customer_id"],
                    idempotency_key=data["idempotency_key"],
                    observations=data.get("observations", ""),
                    items=[CreateOrderItemInput(**item) for item in data["items"]],
                )
            )
        except NotFoundError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ConflictError as e:
            # Estoque insuficiente / produto inativo / cliente inativo etc.
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except BusinessError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        payload = OrderDetailSerializer(order).data
        return Response(payload, status=status.HTTP_200_OK if existed else status.HTTP_201_CREATED)


class OrderDetailCancelView(generics.RetrieveDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer
    permission_classes = [ProfilePermission]
    allowed_profiles_by_method = {
        "GET": ["admin", "manager", "operator", "viewer"],
        "DELETE": ["admin", "manager"],
    }

    def delete(self, request, *args, **kwargs):
        order = self.get_object()
        note = ""
        if isinstance(request.data, dict):
            note = request.data.get("note", "") or ""

        try:
            order = OrderService.cancel_order(order_id=order.id, user=None, note=note)
        except ConflictError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except BusinessError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderDetailSerializer(order).data, status=status.HTTP_200_OK)


class OrderStatusPatchView(generics.GenericAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderStatusPatchSerializer
    permission_classes = [ProfilePermission]
    allowed_profiles_by_method = {
        "PATCH": ["admin", "manager", "operator"],
    }

    def patch(self, request, *args, **kwargs):
        order = self.get_object()

        serializer = OrderStatusPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        note = serializer.validated_data.get("note", "") or ""

        try:
            order = OrderService.change_status(order_id=order.id, new_status=new_status, user=None, note=note)
        except ConflictError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except BusinessError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderDetailSerializer(order).data, status=status.HTTP_200_OK)
