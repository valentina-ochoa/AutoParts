import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from api.forms import RegistroUsuarioForm
from api.models import Producto, Carrito, CarritoItem, ClienteDistribuidor
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

def dashboard(request):
    from api.models import Pedido, PedidoItem, Usuario
    productos = Producto.objects.all()
    nombre = request.GET.get('nombre', '').strip()
    estado = request.GET.get('estado', '').strip()
    proveedor = request.GET.get('proveedor', '').strip()
    precio_min = request.GET.get('precio_min', '').strip()
    precio_max = request.GET.get('precio_max', '').strip()
    stock_min = request.GET.get('stock_min', '').strip()
    stock_max = request.GET.get('stock_max', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    sort = request.GET.get('sort', '').strip()
    dir = request.GET.get('dir', '').strip()
    # Filtros para productos
    if nombre:
        productos = productos.filter(nombre__icontains=nombre)
    if estado:
        productos = productos.filter(estado=estado)
    if proveedor:
        productos = productos.filter(proveedor=proveedor)
    if precio_min:
        productos = productos.filter(precio__gte=precio_min)
    if precio_max:
        productos = productos.filter(precio__lte=precio_max)
    if stock_min:
        productos = productos.filter(stock__gte=stock_min)
    if stock_max:
        productos = productos.filter(stock__lte=stock_max)
    if fecha_desde:
        productos = productos.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        productos = productos.filter(fecha_creacion__date__lte=fecha_hasta)
    # Ordenamiento seguro
    valid_sort_fields = ['nombre', 'precio', 'stock', 'estado', 'fecha_creacion']
    if sort in valid_sort_fields:
        if dir == 'desc':
            productos = productos.order_by(f'-{sort}')
        else:
            productos = productos.order_by(sort)
    proveedores = Producto.objects.values_list('proveedor', flat=True).distinct().exclude(proveedor__isnull=True).exclude(proveedor='')

    # --- Inventario Inteligente ---
    inventario = Producto.objects.all()
    inv_nombre = request.GET.get('inv_nombre', '').strip()
    inv_estado = request.GET.get('inv_estado', '').strip()
    inv_proveedor = request.GET.get('inv_proveedor', '').strip()
    inv_stock_min = request.GET.get('inv_stock_min', '').strip()
    inv_stock_max = request.GET.get('inv_stock_max', '').strip()
    inv_rotacion_min = request.GET.get('rotacion_min', '').strip()
    inv_rotacion_max = request.GET.get('rotacion_max', '').strip()
    inv_fecha_desde = request.GET.get('inv_fecha_desde', '').strip()
    inv_fecha_hasta = request.GET.get('inv_fecha_hasta', '').strip()
    # Filtros inventario
    if inv_nombre:
        inventario = inventario.filter(Q(nombre__icontains=inv_nombre) | Q(marca__icontains=inv_nombre))
    if inv_estado:
        inventario = inventario.filter(estado=inv_estado)
    if inv_proveedor:
        inventario = inventario.filter(proveedor=inv_proveedor)
    if inv_stock_min:
        inventario = inventario.filter(stock__gte=inv_stock_min)
    if inv_stock_max:
        inventario = inventario.filter(stock__lte=inv_stock_max)
    # Rotación y última venta (simulado: rotación=stock/3, última venta=fecha_actualización)
    inventario_list = []
    for p in inventario:
        inventario_list.append({
            'id': p.id,
            'nombre': p.nombre,
            'marca': p.marca,
            'proveedor': p.proveedor,
            'stock': p.stock,
            'rotacion': round(p.stock/3, 1) if p.stock else 0,  # Simulación
            'estado': p.estado,
            'ultima_venta': p.fecha_actualizacion,
        })
    # --- Pedidos y Ventas ---
    pedidos = Pedido.objects.all()
    filtro_cliente = request.GET.get('cliente', '').strip()
    filtro_estado = request.GET.get('estado', '').strip()
    filtro_fecha_desde = request.GET.get('fecha_desde', '').strip()
    filtro_fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    if filtro_cliente:
        pedidos = pedidos.filter(cliente__icontains=filtro_cliente)
    if filtro_estado:
        pedidos = pedidos.filter(estado=filtro_estado)
    if filtro_fecha_desde:
        pedidos = pedidos.filter(fecha__date__gte=filtro_fecha_desde)
    if filtro_fecha_hasta:
        pedidos = pedidos.filter(fecha__date__lte=filtro_fecha_hasta)
    pedidos = pedidos.order_by('-fecha')
    pedidos_list = []
    for p in pedidos:
        pedidos_list.append({
            'id': p.id,
            'fecha': p.fecha,
            'cliente': p.cliente,
            'tipo': p.tipo,
            'total': p.total,
            'estado': p.estado,
            'items': [
                {
                    'producto': item.producto.nombre,
                    'cantidad': item.cantidad,
                    'precio_unitario': item.precio_unitario,
                } for item in p.items.all()
            ]
        })
    return render(request, 'pages/dashboard.html', {
        'productos': productos,
        'proveedores': proveedores,
        'inventario': inventario_list,
        'pedidos': pedidos_list,
    })

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



