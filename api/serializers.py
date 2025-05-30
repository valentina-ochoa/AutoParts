from rest_framework import serializers
from .models import Producto

class ProductoSerializer(serializers.ModelSerializer):
    codigo_del_producto = serializers.CharField(source='codigo_producto')
    codigo = serializers.CharField(source='codigo_interno')
    marca = serializers.CharField()
    nombre = serializers.CharField()
    stock = serializers.IntegerField()
    descripcion = serializers.CharField()
    imagen = serializers.ImageField()
    slug = serializers.SlugField(read_only=True)

    class Meta:
        model = Producto
        fields = [
            'codigo_del_producto',
            'marca',
            'codigo',
            'nombre',
            'stock',
            'descripcion',
            'imagen',
            'slug',
            'precios'
        ]