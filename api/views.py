from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .forms import RegistroUsuarioForm
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType

from .models import Producto, Carrito, CarritoItem


def api_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({'success': True}, status=200)
        else:
            return JsonResponse({'success': False, 'login_error': 'Usuario o contraseña incorrectos'}, status=400)
    return JsonResponse({'login_error': 'Método no permitido'}, status=405)

def log_out(request):
    logout(request)
    return redirect('home')


def iniciar_pago(request):
    print("[iniciar_pago] INICIO")
    # Obtener productos desde el carrito (usando sesión o cookie)
    carrito = request.session.get("carrito", [])
    print(f"[iniciar_pago] Carrito en sesión: {carrito}")

    # Si el carrito de sesión está vacío, intentar leer desde la cookie
    if not carrito:
        carrito_cookie = request.COOKIES.get('carrito')
        print(f"[iniciar_pago] Carrito en cookie: {carrito_cookie}")
        if carrito_cookie:
            try:
                carrito_data = json.loads(carrito_cookie)
                carrito = []
                for item in carrito_data.values():
                    try:
                        producto = Producto.objects.get(pk=item['producto_id'])
                        carrito.append({
                            'id': producto.id,
                            'nombre': producto.nombre,
                            'precio': producto.precio,
                            'cantidad': item['cantidad'],
                        })
                    except Producto.DoesNotExist:
                        continue
                print(f"[iniciar_pago] Carrito reconstruido desde cookie: {carrito}")
            except Exception as e:
                print(f"[iniciar_pago] Error al leer cookie: {e}")
                carrito = []

    if not carrito:
        print("[iniciar_pago] Carrito vacío, redirigiendo a /carrito/")
        messages.error(request, "Tu carrito está vacío.")
        return redirect('/carrito/')

    # Calcular el monto total en CLP
    monto_clp = sum(item['precio'] * item.get('cantidad', 1) for item in carrito)
    print(f"[iniciar_pago] Monto total CLP: {monto_clp}")

    # Datos para Transbank
    buy_order = "ORDEN123"  # puedes usar uuid.uuid4() si deseas que sea único
    session_id = "SESSION123"
    # return_url debe apuntar a la vista de confirmación, no a exito directo
    return_url = request.build_absolute_uri(reverse('confirmar_pago'))
    print(f"[iniciar_pago] return_url: {return_url}")

    transaction = Transaction(WebpayOptions(
        commerce_code=settings.TRANSBANK_COMMERCE_CODE,
        api_key=settings.TRANSBANK_API_KEY,
        integration_type=IntegrationType.TEST
    ))

    try:
        print("[iniciar_pago] Creando transacción con Transbank...")
        response = transaction.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=int(monto_clp),  # asegúrate de que sea int
            return_url=return_url
        )
        print(f"[iniciar_pago] Respuesta de Transbank: {response}")
        return redirect(f"{response['url']}?token_ws={response['token']}")
    except Exception as e:
        print(f"[iniciar_pago] ERROR: {e}")
        messages.error(request, f'Error al iniciar el pago: {str(e)}')
        return redirect('/carrito/')

def confirmar_pago(request):
    token = request.GET.get("token_ws")
    tbk_token = request.GET.get("TBK_TOKEN")
    tbk_order = request.GET.get("TBK_ORDEN_COMPRA")
    tbk_session = request.GET.get("TBK_ID_SESION")
    print(f"[confirmar_pago] token_ws={token}, TBK_TOKEN={tbk_token}, TBK_ORDEN_COMPRA={tbk_order}, TBK_ID_SESION={tbk_session}")

    # Si existe TBK_TOKEN, es un pago cancelado o fallido
    if tbk_token:
        print("[confirmar_pago] Pago cancelado por el usuario o fallido")
        return redirect('pago_cancelado')

    if not token:
        messages.error(request, "Token de pago no recibido.")
        return redirect("carrito")

    transaction = Transaction(WebpayOptions(
        commerce_code=settings.TRANSBANK_COMMERCE_CODE,
        api_key=settings.TRANSBANK_API_KEY,
        integration_type=IntegrationType.TEST
    ))

    try:
        response = transaction.commit(token)
        print(f"[confirmar_pago] Respuesta de Transbank: {response}")
        if response['status'] == 'AUTHORIZED':
            cart = get_or_create_cart(request)
            if cart:
                cart.items.all().delete()
            messages.success(request, "Pago exitoso.")
            return redirect('pago_exito')
        else:
            messages.error(request, f"Pago fallido: {response['status']}")
            return redirect('pago_cancelado')
    except Exception as e:
        print(f"[confirmar_pago] ERROR: {e}")
        messages.error(request, f"Error al confirmar pago: {str(e)}")
        return redirect('pago_cancelado')

def pago_exito(request):
    return render(request, "pages/pago_exito.html")

def pago_cancelado(request):
    return render(request, "pages/pago_cancelado.html")

@csrf_exempt
@require_POST
def agregar_al_carrito(request):
    data = json.loads(request.body)
    producto_id = data.get('producto_id')
    cantidad = int(data.get('cantidad', 1))
    try:
        producto = Producto.objects.get(pk=producto_id)
    except Producto.DoesNotExist:
        return JsonResponse({"status": "error", "msg": "Producto no existe"})
    if request.user.is_authenticated:
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        item, created = CarritoItem.objects.get_or_create(carrito=carrito, producto=producto)
        if not created:
            item.cantidad += cantidad
        else:
            item.cantidad = cantidad
        item.save()
        carrito_items = carrito.items.select_related('producto').all()
        carrito_total = carrito.total()
        cart_count = sum(i.cantidad for i in carrito_items)
        productos = []
        for item in carrito_items:
            productos.append({
                "id": item.producto.id,
                "nombre": item.producto.nombre,
                "precio": item.producto.precio,
                "cantidad": item.cantidad,
                "imagen": item.producto.imagen.url if item.producto.imagen else "",
                "subtotal": item.subtotal(),
            })
        return JsonResponse({
            "status": "ok",
            "cart_total": carrito_total,
            "cart_count": cart_count,
            "productos": productos,
        })
    else:
        carrito = request.COOKIES.get('carrito')
        if carrito:
            carrito_data = json.loads(carrito)
        else:
            carrito_data = {}
        if str(producto_id) in carrito_data:
            carrito_data[str(producto_id)]['cantidad'] += cantidad
        else:
            carrito_data[str(producto_id)] = {'producto_id': producto_id, 'cantidad': cantidad}
        carrito_items = []
        carrito_total = 0
        cart_count = 0
        productos = []
        for item in carrito_data.values():
            try:
                p = Producto.objects.get(pk=item['producto_id'])
                subtotal = p.precio * item['cantidad']
                carrito_items.append({
                    'producto': p,
                    'cantidad': item['cantidad'],
                    'subtotal': subtotal,
                })
                carrito_total += subtotal
                cart_count += item['cantidad']
                productos.append({
                    "id": p.id,
                    "nombre": p.nombre,
                    "precio": p.precio,
                    "cantidad": item['cantidad'],
                    "imagen": p.imagen.url if p.imagen else "",
                    "subtotal": subtotal,
                })
            except Producto.DoesNotExist:
                continue
        response = JsonResponse({
            "status": "ok",
            "cart_total": carrito_total,
            "cart_count": cart_count,
            "productos": productos,
        })
        response.set_cookie('carrito', json.dumps(carrito_data), max_age=60*60*24*7, path='/')
        return response

@csrf_exempt
@require_POST
def eliminar_del_carrito(request, item_id):
    if request.user.is_authenticated:
        try:
            item = CarritoItem.objects.get(id=item_id, carrito__usuario=request.user)
            item.delete()
            carrito = item.carrito
            carrito_items = carrito.items.select_related('producto').all()
            carrito_total = carrito.total()
            cart_count = sum(i.cantidad for i in carrito_items)
        except CarritoItem.DoesNotExist:
            carrito_items = []
            carrito_total = 0
            cart_count = 0
        productos = []
        for item in carrito_items:
            producto = item.producto
            cantidad = item.cantidad
            subtotal = item.subtotal()
            productos.append({
                "id": producto.id,
                "nombre": producto.nombre,
                "precio": producto.precio,
                "cantidad": cantidad,
                "imagen": producto.imagen.url if producto.imagen else "",
                "subtotal": subtotal,
            })
        return JsonResponse({
            "status": "ok",
            "cart_total": carrito_total,
            "cart_count": cart_count,
            "productos": productos,
        })
    else:
        carrito = request.COOKIES.get('carrito')
        carrito_items = []
        carrito_total = 0
        cart_count = 0
        if carrito:
            carrito_data = json.loads(carrito)
            if str(item_id) in carrito_data:
                del carrito_data[str(item_id)]
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
                    cart_count += cantidad
                except Producto.DoesNotExist:
                    continue
            productos = []
            for item in carrito_items:
                producto = item["producto"]
                cantidad = item["cantidad"]
                subtotal = item["subtotal"]
                productos.append({
                    "id": producto.id,
                    "nombre": producto.nombre,
                    "precio": producto.precio,
                    "cantidad": cantidad,
                    "imagen": producto.imagen.url if producto.imagen else "",
                    "subtotal": subtotal,
                })
            response = JsonResponse({
                "status": "ok",
                "cart_total": carrito_total,
                "cart_count": cart_count,
                "productos": productos,
            })
            response.set_cookie('carrito', json.dumps(carrito_data), max_age=60*60*24*7, path='/')
            return response
        else:
            productos = []
            response = JsonResponse({
                "status": "ok",
                "cart_total": 0,
                "cart_count": 0,
                "productos": productos,
            })
            response.set_cookie('carrito', json.dumps({}), max_age=60*60*24*7, path='/')
            return response

@csrf_exempt
@require_POST
def actualizar_cantidad_carrito(request):
    data = json.loads(request.body)
    producto_id = data.get('producto_id')
    cantidad = int(data.get('cantidad', 1))
    if cantidad < 1:
        cantidad = 1
    if request.user.is_authenticated:
        try:
            item = CarritoItem.objects.get(carrito__usuario=request.user, producto_id=producto_id)
            item.cantidad = cantidad
            item.save()
            subtotal = item.subtotal()
            carrito = item.carrito
            total = carrito.total()
            return JsonResponse({"status": "ok", "subtotal": subtotal, "total": total})
        except CarritoItem.DoesNotExist:
            return JsonResponse({"status": "error"})
    else:
        carrito = request.COOKIES.get('carrito')
        if carrito:
            carrito_data = json.loads(carrito)
        else:
            carrito_data = {}
        if str(producto_id) in carrito_data:
            carrito_data[str(producto_id)]['cantidad'] = cantidad
        try:
            producto = Producto.objects.get(pk=producto_id)
            subtotal = producto.precio * cantidad
        except Producto.DoesNotExist:
            subtotal = 0
        total = 0
        for item in carrito_data.values():
            try:
                p = Producto.objects.get(pk=item['producto_id'])
                total += p.precio * item['cantidad']
            except Producto.DoesNotExist:
                continue
        response = JsonResponse({"status": "ok", "subtotal": subtotal, "total": total})
        response.set_cookie('carrito', json.dumps(carrito_data), max_age=60*60*24*7)
        return response
    return JsonResponse({"status": "error"})

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
    if request.user.is_authenticated:
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            carrito.items.all().delete()
        except Carrito.DoesNotExist:
            pass
        return redirect('carrito')
    response = redirect('carrito')
    response.set_cookie('carrito', json.dumps({}), max_age=60*60*24*7, path='/')
    return response

def limpiar_carrito_y_volver_inicio(request):
    if request.user.is_authenticated:
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            carrito.items.all().delete()
        except Carrito.DoesNotExist:
            pass
        return redirect('home')
    response = redirect('home')
    response.set_cookie('carrito', json.dumps({}), max_age=60*60*24*7, path='/')
    return response

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Carrito.objects.get_or_create(usuario=request.user)
        cart.total_calculado = cart.total()
        cart.total_usd_calculado = round(cart.total_calculado / 850, 2)  
        return cart
    return None

@csrf_exempt
def editar_producto(request):
    """API para editar un producto desde el dashboard admin."""
    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        nombre = request.POST.get('nombre')
        codigo = request.POST.get('codigo')
        proveedor = request.POST.get('proveedor')
        precio = request.POST.get('precio')
        stock = request.POST.get('stock')
        estado = request.POST.get('estado')
        try:
            producto = Producto.objects.get(pk=producto_id)
            producto.nombre = nombre
            producto.proveedor = proveedor
            producto.precio = int(precio)
            producto.stock = int(stock)
            producto.estado = estado
            producto.save()
            return JsonResponse({'status': 'ok'})
        except Producto.DoesNotExist:
            return JsonResponse({'status': 'error', 'msg': 'Producto no encontrado'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)})
    return JsonResponse({'status': 'error', 'msg': 'Método no permitido'})

@csrf_exempt
def accion_masiva_producto(request):
    """API para acciones masivas sobre productos: activar, inactivar, descontinuar."""
    if request.method == 'POST':
        ids = request.POST.get('ids', '')
        accion = request.POST.get('accion')
        id_list = [int(i) for i in ids.split(',') if i.isdigit()]
        if not id_list or accion not in ['activo', 'inactivo', 'descontinuado']:
            return JsonResponse({'status': 'error', 'msg': 'Datos inválidos'})
        try:
            Producto.objects.filter(id__in=id_list).update(estado=accion)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)})
    return JsonResponse({'status': 'error', 'msg': 'Método no permitido'})

@csrf_exempt
@require_POST
def eliminar_producto(request):
    """API para eliminar un producto desde el dashboard admin."""
    producto_id = request.POST.get('producto_id')
    if not producto_id:
        return JsonResponse({'status': 'error', 'msg': 'ID de producto requerido'})
    try:
        producto = Producto.objects.get(pk=producto_id)
        producto.delete()
        return JsonResponse({'status': 'ok'})
    except Producto.DoesNotExist:
        return JsonResponse({'status': 'error', 'msg': 'Producto no encontrado'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@csrf_exempt
@require_POST
def crear_producto(request):
    """API para crear un nuevo producto desde el dashboard admin."""
    nombre = request.POST.get('nombre')
    proveedor = request.POST.get('proveedor')
    precio = request.POST.get('precio')
    stock = request.POST.get('stock')
    estado = request.POST.get('estado') or 'inactivo'
    if not (nombre  and precio and stock):
        return JsonResponse({'status': 'error', 'msg': 'Faltan campos obligatorios'})
    try:
        if int(precio) <= 0:
            return JsonResponse({'status': 'error', 'msg': 'El precio debe ser mayor a 0'})
    except Exception:
        return JsonResponse({'status': 'error', 'msg': 'Precio inválido'})
    # Verificar unicidad de código y nombre
    from .models import Producto
    if Producto.objects.filter(nombre=nombre).exists():
        return JsonResponse({'status': 'error', 'msg': 'Ya existe un producto con ese nombre'})
    try:
        producto = Producto.objects.create(
            nombre=nombre,
            proveedor=proveedor,
            precio=int(precio),
            stock=int(stock),
            estado=estado
        )
        return JsonResponse({'status': 'ok', 'id': producto.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})



