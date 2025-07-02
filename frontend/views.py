import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from api.forms import RegistroUsuarioForm
from api.models import Producto, Carrito, ClienteDistribuidor
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.integration_type import IntegrationType
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

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
                        producto = Producto.objects.get(pk=item['id'])
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

def tienda(request, query=None):
    # Permitir /tienda/<query>/ y /tienda/?q=<query>
    if query is None:
        query = request.GET.get('q', '').strip()
    else:
        query = query.strip()
    if query:
        productos = Producto.objects.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query)
        )
    else:
        productos = Producto.objects.all()
    context = {
        'productos': productos,
        'query': query,
    }
    return render(request, 'pages/productos_busqueda.html', context)

def producto(request, id=None):
    if id is not None:
        producto = get_object_or_404(Producto, id=id)
        return render(request, 'pages/product.html', {'producto': producto})
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
    iva = 0
    neto = 0

    if request.user.is_authenticated:
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            carrito_items = carrito.items.select_related('producto').all()
            from api.models import ClienteDistribuidor
            es_distribuidor = ClienteDistribuidor.objects.filter(email=request.user.email, tipo='distribuidor', activo=True).exists()
            es_superuser = request.user.is_superuser

            for item in carrito_items:
                precio_item = item.producto.precio_mayorista if (es_distribuidor or es_superuser) else item.producto.precio
                items.append({
                    'producto': item.producto,
                    'cantidad': item.cantidad,
                    'subtotal': precio_item * item.cantidad,
                    'precio_unitario': precio_item,
                })
                total += precio_item * item.cantidad
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
                        precio_item = producto.precio_mayorista if item.get('mayorista') else producto.precio
                        subtotal = precio_item * cantidad
                        items.append({
                            'producto': producto,
                            'cantidad': cantidad,
                            'subtotal': subtotal,
                            'precio_unitario': precio_item,
                        })
                        total += subtotal
                    except Producto.DoesNotExist:
                        continue
            except Exception:
                items = []
                total = 0

    if total:
        neto = round(total / 1.19)
        iva = total - neto
    else:
        neto = 0
        iva = 0

    context = {
        'items': items,
        'total': total,
        'iva': iva,
        'neto': neto,
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

@login_required
def mayorista(request):
    # Permitir acceso a distribuidores activos o superusuarios
    es_distribuidor = ClienteDistribuidor.objects.filter(email=request.user.email, tipo='distribuidor', activo=True).exists()
    if not (es_distribuidor or request.user.is_superuser):
        return HttpResponseForbidden("Acceso solo para distribuidores.")
    productos = Producto.objects.filter(estado='activo')
    context = {
        'productos': productos,
    }
    return render(request, 'pages/mayorista.html', context)

def store(request):
    return render(request, 'pages/store.html')

