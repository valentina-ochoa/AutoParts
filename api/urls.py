from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.api_login, name='login'),
    path('logout/', views.log_out, name='logout'),
    path('pago/iniciar/', views.iniciar_pago, name='iniciar_pago'),
    path('pago/confirmar/', views.confirmar_pago, name='confirmar_pago'),
    path('pago/exito/', views.pago_exito, name='pago_exito'),
    path('pago/cancelado/', views.pago_cancelado, name='pago_cancelado'),
    # Carrito API
    path('agregar-al-carrito/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('actualizar-cantidad-carrito/', views.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),
    path('eliminar-del-carrito/<int:item_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('carrito/limpiar/', views.limpiar_carrito, name='limpiar_carrito'),
    path('volver-inicio/', views.limpiar_carrito_y_volver_inicio, name='volver_inicio'),

]