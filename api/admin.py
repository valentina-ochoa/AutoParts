from django.contrib import admin
from .models import CarritoItem, Pedido, PedidoItem, LogEntryProxy
import json

admin.site.site_header = "Panel de Administración"
admin.site.site_title = "Administración de Tienda"
admin.site.index_title = "Dashboard"

admin.site.register(CarritoItem)

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

@admin.register(LogEntryProxy)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'objeto_afectado', 'action_flag', 'mensaje_legible')
    search_fields = ('user__username', 'object_repr', 'change_message')

    def objeto_afectado(self, obj):
        return obj.object_repr
    objeto_afectado.short_description = "Objeto afectado"

    def mensaje_legible(self, obj):
        try:
            data = json.loads(obj.change_message)
            if isinstance(data, list) and data and "changed" in data[0]:
                fields = data[0]["changed"].get("fields", [])
                if fields:
                    return "Campos modificados: " + ", ".join(fields)
            elif isinstance(data, list) and data and "added" in data[0]:
                return "Objeto agregado"
            elif isinstance(data, list) and data and "deleted" in data[0]:
                return "Objeto eliminado"
        except Exception:
            pass
        return obj.change_message or "-"
    mensaje_legible.short_description = "Mensaje de cambio"

    def has_delete_permission(self, request, obj=None):
        return False

    actions = None