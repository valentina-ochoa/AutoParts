from django.contrib import admin
from .models import Producto, Usuario, Carrito, CarritoItem

admin.site.register(Producto)
admin.site.register(Usuario)
admin.site.register(Carrito)
admin.site.register(CarritoItem)
