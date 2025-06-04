from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify

class Usuario(AbstractUser):
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=15, null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Nacimiento")
    direccion = models.CharField(max_length=255, null=True, blank=True, verbose_name="Dirección")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")

    def __str__(self):
        return self.username

class Producto(models.Model):
    codigo_producto = models.CharField(max_length=50, unique=True, verbose_name="Código del Producto")
    marca = models.CharField(max_length=100)
    codigo_interno = models.CharField(max_length=50, unique=True, verbose_name="Código Interno")
    nombre = models.CharField(max_length=200)
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock Disponible")
    imagen = models.ImageField(upload_to='imgProductos/', null=True, blank=True, verbose_name="Imagen del Producto")
    descripcion = models.TextField(null=True, blank=True, verbose_name="Descripción del Producto")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")
    precio = models.IntegerField(default=999999999, verbose_name="Precio Base (CLP)")  # Valor por defecto de 999999999 CLP
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
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.nombre} ({self.codigo_producto})"

    
class Carrito(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, default='activo')

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