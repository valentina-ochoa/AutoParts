from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.conf import settings

class Usuario(AbstractUser):
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=15, null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Nacimiento")
    direccion = models.CharField(max_length=255, null=True, blank=True, verbose_name="Dirección")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")

    def __str__(self):
        return self.username

class Producto(models.Model):
    marca = models.CharField(max_length=100)
    nombre = models.CharField(max_length=200)
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock Disponible")
    imagen = models.ImageField(upload_to='imgProductos/', null=True, blank=True, verbose_name="Imagen del Producto")
    descripcion = models.TextField(null=True, blank=True, verbose_name="Descripción del Producto")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")
    precio = models.IntegerField(default=999999999, verbose_name="Precio Base (CLP)")  # Valor por defecto de 999999999 CLP
    precio_mayorista = models.IntegerField(default=999999999, verbose_name="Precio Mayorista (CLP)")  # Valor por defecto de 999999999 CLP
    etiquetas = models.CharField(max_length=255, null=True, blank=True, verbose_name="Etiquetas del Producto")

    estado = models.CharField(max_length=20, default='activo', choices=[
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('descontinuado', 'Descontinuado')
    ], verbose_name="Estado del Producto")

    proveedor = models.CharField(max_length=100, null=True, blank=True, verbose_name="Proveedor")
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        # Calcular precio mayorista automáticamente
        if self.precio is not None:
            self.precio_mayorista = int(self.precio - (self.precio * 0.25))
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.nombre} (ID: {self.id})"

    
class Carrito(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Carrito"
        verbose_name_plural = "Carritos"

    def __str__(self):
        return f"Carrito de {self.usuario.username}"

    def total(self):
        return sum(item.subtotal() for item in self.items.all())

class CarritoItem(models.Model):
    carrito = models.ForeignKey(Carrito, related_name='items', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Carrito Item"
        verbose_name_plural = "Carrito Items"
        unique_together = ('carrito', 'producto')

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    def subtotal(self):
        return self.cantidad * self.producto.precio

class Pedido(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pedidos')
    tipo = models.CharField(max_length=10, choices=[('pedido', 'Pedido'), ('venta', 'Venta')], default='pedido')
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=[('pendiente', 'Pendiente'), ('procesado', 'Procesado'), ('entregado', 'Entregado'), ('cancelado', 'Cancelado')], default='pendiente')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observaciones = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.get_full_name()} - {self.fecha.strftime('%Y-%m-%d')}"

class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='items', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre} (Pedido #{self.pedido.id})"

class ClienteDistribuidor(models.Model):
    tipo = models.CharField(max_length=20, choices=[('cliente', 'Cliente'), ('distribuidor', 'Distribuidor')], default='cliente')
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Cliente o Distribuidor"
        verbose_name_plural = "Clientes y Distribuidores"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"

class LogEntryProxy(LogEntry):
    class Meta:
        proxy = True
        verbose_name = "Log"
        verbose_name_plural = "Logs"

class CarritoItemInline(admin.TabularInline):
    model = CarritoItem
    extra = 0

@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    inlines = [CarritoItemInline]
    list_display = ("usuario", "creado", "total")
    search_fields = ("usuario__username",)

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    readonly_fields = ("date_joined", "fecha_actualizacion", "last_login")

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    readonly_fields = ("fecha_creacion", "fecha_actualizacion", "slug")

@admin.register(ClienteDistribuidor)
class ClienteDistribuidorAdmin(admin.ModelAdmin):
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
