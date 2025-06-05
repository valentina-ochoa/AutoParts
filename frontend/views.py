import json
from django.http import JsonResponse
from django.shortcuts import render, redirect
from api.forms import RegistroUsuarioForm
from api.models import Producto, Carrito, CarritoItem
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.integration_type import IntegrationType

def index(request):
    productos = Producto.objects.all()
    carrito_items = []
    carrito_total = 0

    if request.user.is_authenticated:
        # Usuario logueado: usa el modelo
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            carrito_items = carrito.items.select_related('producto').all()
            carrito_total = carrito.total()
        except Carrito.DoesNotExist:
            carrito_items = []
            carrito_total = 0
    else:
        # Usuario no logueado: usa cookies
        carrito_cookie = request.COOKIES.get('carrito')
        if carrito_cookie:
            try:
                carrito_data = json.loads(carrito_cookie)
                for item in carrito_data.values():
                    try:
                        producto = Producto.objects.get(pk=item['producto_id'])
                        cantidad = item['cantidad']
                        subtotal = producto.precio * cantidad
                        carrito_items.append({
                            'producto': producto,
                            'cantidad': cantidad,
                            'subtotal': subtotal,
                        })
                        carrito_total += subtotal
                    except Producto.DoesNotExist:
                        continue
            except Exception:
                carrito_items = []
                carrito_total = 0

    context = {
        'productos': productos,
        'carrito_items': carrito_items,
        'carrito_total': carrito_total,
    }
    return render(request, 'pages/index.html', context)

def tienda(request):
    return render(request, 'pages/store.html')

def producto(request):
    return render(request, 'pages/product.html')

def checkout(request):
    return render(request, 'pages/checkout.html')

def account(request):
    return render(request, 'pages/account.html')

def register(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = RegistroUsuarioForm()
    return render(request, 'pages/register.html', {'form': form})

@csrf_exempt
def carrito_view(request):
    items = []
    total = 0

    if request.user.is_authenticated:
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            carrito_items = carrito.items.select_related('producto').all()
            for item in carrito_items:
                items.append({
                    'producto': item.producto,
                    'cantidad': item.cantidad,
                    'subtotal': item.subtotal(),
                })
                total += item.subtotal()
        except Carrito.DoesNotExist:
            items = []
            total = 0
    else:
        carrito_cookie = request.COOKIES.get('carrito')
        if carrito_cookie:
            try:
                carrito_data = json.loads(carrito_cookie)
                for item in carrito_data.values():
                    try:
                        producto = Producto.objects.get(pk=item['producto_id'])
                        cantidad = item['cantidad']
                        subtotal = producto.precio * cantidad
                        items.append({
                            'producto': producto,
                            'cantidad': cantidad,
                            'subtotal': subtotal,
                        })
                        total += subtotal
                    except Producto.DoesNotExist:
                        continue
            except Exception:
                items = []
                total = 0

    context = {
        'items': items,
        'total': total,
    }
    return render(request, 'pages/carrito.html', context)

def limpiar_carrito(request):
    # Limpia el carrito del usuario logueado
    if request.user.is_authenticated:
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            carrito.items.all().delete()
        except Carrito.DoesNotExist:
            pass
        return redirect('carrito')
    # Limpia el carrito en la cookie para usuarios no logueados
    response = redirect('carrito')
    response.set_cookie('carrito', json.dumps({}), max_age=60*60*24*7, path='/')
    return response

def limpiar_carrito_y_volver_inicio(request):
    # Limpia el carrito del usuario logueado
    if request.user.is_authenticated:
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            carrito.items.all().delete()
        except Carrito.DoesNotExist:
            pass
        return redirect('home')
    # Limpia el carrito en la cookie para usuarios no logueados
    response = redirect('home')
    response.set_cookie('carrito', json.dumps({}), max_age=60*60*24*7, path='/')
    return response

def dashboard(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('home')
    
    productos = Producto.objects.all()
    context = {
        'productos': productos,
    }
    return render(request, 'pages/dashboard.html', context)



