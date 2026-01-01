from django.urls import path
from . import views

app_name = 'carts'

urlpatterns = [
    path('add/', views.CartAddView.as_view(), name='cart_add'),
    path('change/', views.CartChangeView.as_view(), name='cart_change'),
    path('remove/', views.CartRemoveView.as_view(), name='cart_remove'),
    path('view/', views.CartDetailView.as_view(), name='cart_view'),
]