from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('tienda/', views.tienda, name='store'),
    path('producto/', views.producto, name='product'),
    path('checkout/', views.checkout, name='checkout'),
    path('cuenta/', views.account, name='account'),
    path('registrarse/', views.register, name='register'),
]
