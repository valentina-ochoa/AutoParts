from django.urls import path, re_path
from . import views
from .views import change_password

urlpatterns = [
    path('', views.index, name='home'),
    path('tienda/', views.tienda, name='productos_busqueda'),
    re_path(r'^tienda/(?P<query>[^/]+)/$', views.tienda, name='productos_busqueda_query'),
    path('producto/', views.producto, name='product'),
    path('producto/<int:id>/', views.producto, name='product_detail'),
    path('checkout/', views.checkout, name='checkout'),
    path('cuenta/', views.account, name='account'),
    path('registrarse/', views.register, name='register'),
    path('carrito/', views.carrito_view, name='carrito'),
    path('mayorista/', views.mayorista, name='mayorista'),
    path('tienda/', views.store, name='store'),
    path('cambiar_contraseña/', change_password, name='cambiar_contraseña'),
    path('catalogo/', views.catalogo, name='catalogo'),
]
