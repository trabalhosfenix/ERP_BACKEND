from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import OrderCreateSerializer, OrderOutSerializer
from .services.order_service import OrderService, CreateOrderInput, CreateOrderItemInput, BusinessError

class OrderCreateView(APIView):
    def post(self, request):
        ser = OrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            order = OrderService.create_order(
                CreateOrderInput(
                    customer_id=data['customer_id'],
                    idempotency_key=data['idempotency_key'],
                    observations=data.get('observations', ''),
                    items=[CreateOrderItemInput(**it) for it in data['items']],
                )
            )
        except BusinessError as e:
            return Response({'detail': str(e)}, status=getattr(e, 'status_code', 400))

        return Response(OrderOutSerializer(order).data, status=status.HTTP_201_CREATED)

from .services.order_service import ConflictError, NotFoundError
from .serializers import OrderStatusPatchSerializer
from apps.orders.models import Order
from rest_framework import generics

class OrderListView(generics.ListAPIView):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderOutSerializer

class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderOutSerializer

class OrderStatusPatchView(APIView):
    def patch(self, request, pk: int):
        ser = OrderStatusPatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            order = OrderService.change_status(
                order_id=pk,
                new_status=ser.validated_data['status'],
                user=request.user if request.user.is_authenticated else None,
                note=ser.validated_data.get('note', '')
            )
        except (BusinessError, ConflictError, NotFoundError) as e:
            return Response({'detail': str(e)}, status=getattr(e, 'status_code', 400))

        return Response(OrderOutSerializer(order).data)

class OrderCancelView(APIView):
    def delete(self, request, pk: int):
        try:
            order = OrderService.cancel_order(
                order_id=pk,
                user=request.user if request.user.is_authenticated else None,
                note='cancelled via api'
            )
        except (BusinessError, ConflictError, NotFoundError) as e:
            return Response({'detail': str(e)}, status=getattr(e, 'status_code', 400))

        return Response(OrderOutSerializer(order).data)
