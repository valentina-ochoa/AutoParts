from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('tienda/', views.tienda, name='store'),
    path('producto/', views.producto, name='product'),
    path('checkout/', views.checkout, name='checkout'),
    path('cuenta/', views.account, name='account'),
    path('registrarse/', views.register, name='register'),

    # Carrito (DEPRECATED: toda la lógica está en la API, mantener solo la vista de carrito para renderizado)
    # path('carrito/', views.carrito_view, name='carrito'),
    # path('agregar-al-carrito/', views.agregar_al_carrito, name='agregar_al_carrito'),
    # path('actualizar-cantidad-carrito/', views.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),
    # path('eliminar-del-carrito/<int:item_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    # path('carrito/limpiar/', views.limpiar_carrito, name='limpiar_carrito'),
    # path('volver-inicio/', views.limpiar_carrito_y_volver_inicio, name='volver_inicio'),
    path('carrito/', views.carrito_view, name='carrito'),
]
