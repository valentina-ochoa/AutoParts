from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('tienda/', views.tienda, name='store'),
    path('producto/', views.producto, name='product'),
    path('checkout/', views.checkout, name='checkout'),
    path('cuenta/', views.account, name='account'),
    path('registrarse/', views.register, name='register'),
    path('carrito/', views.carrito_view, name='carrito'),
    path('catalogo-externo/', views.catalogo_externo, name='catalogo_externo'),
    path('carrito/limpiar/', views.limpiar_carrito, name='limpiar_carrito'),
    path('pago/exito/', views.pago_exito, name='pago_exito'),
    path('volver-inicio/', views.limpiar_carrito_y_volver_inicio, name='volver_inicio'),




    
]
