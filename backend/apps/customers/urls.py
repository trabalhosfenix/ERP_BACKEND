from django.urls import path
from .views import CustomerListCreateView, CustomerRetrieveView

urlpatterns = [
    path('customers', CustomerListCreateView.as_view(), name='customers-list-create'),
    path('customers/<int:pk>', CustomerRetrieveView.as_view(), name='customers-detail'),
]
