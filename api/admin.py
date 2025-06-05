from django.contrib import admin
from .models import Producto, Usuario, Carrito, CarritoItem, LogAuditoria, Pedido, PedidoItem, ClienteDistribuidor

admin.site.register(Producto)
admin.site.register(Usuario)
admin.site.register(Carrito)
admin.site.register(CarritoItem)
admin.site.register(LogAuditoria)
admin.site.register(ClienteDistribuidor)

class PedidoItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 0

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'tipo', 'fecha', 'estado', 'total')
    list_filter = ('tipo', 'estado', 'fecha')
    search_fields = ('cliente',)
    inlines = [PedidoItemInline]

@admin.register(PedidoItem)
class PedidoItemAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'producto', 'cantidad', 'precio_unitario')
    search_fields = ('pedido__cliente', 'producto__nombre')
