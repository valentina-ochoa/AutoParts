from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.api_login, name='login'),
    path('logout/', views.log_out, name='logout'),
    path('pago/iniciar/', views.iniciar_pago, name='iniciar_pago'),
    path('pago/confirmar/', views.confirmar_pago, name='confirmar_pago'),
    path('pago/exito/', views.pago_exito, name='pago_exito'),

]