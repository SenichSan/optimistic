from django.urls import path
from . import views
from .views import OrderSuccessView

app_name = 'orders'

urlpatterns = [
    path('create-order/', views.CreateOrderView.as_view(), name='create_order'),
    path('order-success/<uuid:order_uuid>/', OrderSuccessView.as_view(), name='order_success'),
    path('ajax/search-city/', views.search_city, name='search_city'),
    path('ajax/get-warehouses/', views.get_warehouses, name='get_warehouses'),
]