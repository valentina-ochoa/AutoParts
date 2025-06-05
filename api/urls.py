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
    path('producto/editar/', views.editar_producto, name='editar_producto'),
    path('producto/accion_masiva/', views.accion_masiva_producto, name='accion_masiva_producto'),
    path('producto/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('producto/crear/', views.crear_producto, name='crear_producto'),
    path('producto/eliminar_masivo/', views.eliminar_masivo_producto, name='eliminar_masivo_producto'),
    path('logs/', views.api_logs, name='api_logs'),
    path('pedidos/', views.api_pedidos, name='api_pedidos'),
    path('pedido/nuevo/', views.api_pedido_nuevo, name='api_pedido_nuevo'),
    path('clientes/', views.api_clientes_distribuidores, name='api_clientes_distribuidores'),
    path('cliente/nuevo/', views.api_nuevo_cliente_distribuidor, name='api_nuevo_cliente_distribuidor'),
    path('dashboard-resumen/', views.api_dashboard_resumen, name='api_dashboard_resumen'),
    path('pedido/terminar/<int:pedido_id>/', views.terminar_pedido, name='terminar_pedido'),
    path('pedido/eliminar/<int:pedido_id>/', views.eliminar_pedido, name='eliminar_pedido'),

]