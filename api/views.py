from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .forms import RegistroUsuarioForm
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import json

from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType

from .models import Producto, Carrito, CarritoItem, Pedido, PedidoItem, ClienteDistribuidor
from django.db.models import Count, Q


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
    carrito = []
    if request.user.is_authenticated:
        # Usuario autenticado: obtener desde modelo
        try:
            carrito_obj = Carrito.objects.get(usuario=request.user)
            from .models import ClienteDistribuidor
            es_distribuidor = ClienteDistribuidor.objects.filter(email=request.user.email, tipo='distribuidor', activo=True).exists()
            es_superuser = request.user.is_superuser
            for item in carrito_obj.items.select_related('producto').all():
                # Usar precio mayorista si corresponde
                precio = item.producto.precio_mayorista if (es_distribuidor or es_superuser) else item.producto.precio
                carrito.append({
                    'id': item.producto.id,
                    'nombre': item.producto.nombre,
                    'precio': precio,
                    'cantidad': item.cantidad,
                })
        except Carrito.DoesNotExist:
            carrito = []
    else:
        # Usuario anónimo: obtener desde cookie
        carrito_cookie = request.COOKIES.get('carrito')
        print(f"[iniciar_pago] Carrito en cookie: {carrito_cookie}")
        if carrito_cookie:
            try:
                carrito_data = json.loads(carrito_cookie)
                for item in carrito_data.values():
                    try:
                        producto = Producto.objects.get(pk=item['producto_id'])
                        usar_mayorista = item.get('mayorista', False)
                        precio = producto.precio_mayorista if usar_mayorista else producto.precio
                        carrito.append({
                            'id': producto.id,
                            'nombre': producto.nombre,
                            'precio': precio,
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
            # --- CREAR PEDIDO ---
            if cart and request.user.is_authenticated:
                from .models import Pedido, PedidoItem
                from .models import ClienteDistribuidor
                es_distribuidor = ClienteDistribuidor.objects.filter(email=request.user.email, tipo='distribuidor', activo=True).exists()
                es_superuser = request.user.is_superuser
                pedido = Pedido.objects.create(
                    usuario=request.user,
                    tipo='pedido',
                    estado='pagado',
                    total=cart.total(),
                    observaciones='Pedido generado automáticamente tras pago Webpay.'
                )
                for item in cart.items.select_related('producto').all():
                    precio_unitario = item.producto.precio_mayorista if (es_distribuidor or es_superuser) else item.producto.precio
                    PedidoItem.objects.create(
                        pedido=pedido,
                        producto=item.producto,
                        cantidad=item.cantidad,
                        precio_unitario=precio_unitario
                    )
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
    usar_mayorista = data.get('mayorista', False)
    try:
        producto = Producto.objects.get(pk=producto_id)
    except Producto.DoesNotExist:
        return JsonResponse({"status": "error", "msg": "Producto no existe"})
    # Determinar precio a usar
    precio_a_usar = producto.precio_mayorista if usar_mayorista else producto.precio
    if request.user.is_authenticated:
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
        item, created = CarritoItem.objects.get_or_create(carrito=carrito, producto=producto)
        if not created:
            item.cantidad += cantidad
        else:
            item.cantidad = cantidad
        item.save()
        carrito_items = carrito.items.select_related('producto').all()
        carrito_total = 0
        cart_count = 0
        productos = []
        for item in carrito_items:
            # Si el producto fue agregado como mayorista, usar ese precio
            precio_item = producto.precio_mayorista if usar_mayorista else item.producto.precio
            subtotal = precio_item * item.cantidad
            carrito_total += subtotal
            cart_count += item.cantidad
            productos.append({
                "id": item.producto.id,
                "nombre": item.producto.nombre,
                "precio": precio_item,
                "cantidad": item.cantidad,
                "imagen": item.producto.imagen.url if item.producto.imagen else "",
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
        if carrito:
            carrito_data = json.loads(carrito)
        else:
            carrito_data = {}
        if str(producto_id) in carrito_data:
            carrito_data[str(producto_id)]['cantidad'] += cantidad
        else:
            carrito_data[str(producto_id)] = {'producto_id': producto_id, 'cantidad': cantidad, 'mayorista': usar_mayorista}
        carrito_items = []
        carrito_total = 0
        cart_count = 0
        productos = []
        for item in carrito_data.values():
            try:
                p = Producto.objects.get(pk=item['producto_id'])
                precio_item = p.precio_mayorista if item.get('mayorista') else p.precio
                subtotal = precio_item * item['cantidad']
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
                    "precio": precio_item,
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
            # Detectar si el usuario es distribuidor activo o superuser
            from api.models import ClienteDistribuidor
            es_distribuidor = ClienteDistribuidor.objects.filter(email=request.user.email, tipo='distribuidor', activo=True).exists()
            es_superuser = request.user.is_superuser
            precio_item = item.producto.precio_mayorista if (es_distribuidor or es_superuser) else item.producto.precio
            subtotal = precio_item * item.cantidad
            carrito = item.carrito
            # Calcular total con lógica de mayorista
            total = 0
            for it in carrito.items.select_related('producto').all():
                precio = it.producto.precio_mayorista if (es_distribuidor or es_superuser) else it.producto.precio
                total += precio * it.cantidad
            neto = round(total / 1.19)
            iva = total - neto
            return JsonResponse({"success": True, "subtotal": subtotal, "total": int(total), "iva": int(iva)})
        except CarritoItem.DoesNotExist:
            return JsonResponse({"success": False})
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
            usar_mayorista = carrito_data.get(str(producto_id), {}).get('mayorista', False)
            precio_item = producto.precio_mayorista if usar_mayorista else producto.precio
            subtotal = precio_item * cantidad
        except Producto.DoesNotExist:
            subtotal = 0
        total = 0
        for item in carrito_data.values():
            try:
                p = Producto.objects.get(pk=item['producto_id'])
                usar_mayorista = item.get('mayorista', False)
                precio = p.precio_mayorista if usar_mayorista else p.precio
                total += precio * item['cantidad']
            except Producto.DoesNotExist:
                continue
        neto = round(total / 1.19)
        iva = total - neto
        response = JsonResponse({"success": True, "subtotal": subtotal, "total": int(total), "iva": int(iva)})
        response.set_cookie('carrito', json.dumps(carrito_data), max_age=60*60*24*7)
        return response
    return JsonResponse({"success": False})

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
    """API para editar un producto desde el dashboard admin, incluyendo imagen."""
    if request.method == 'POST':
        id = request.POST.get('id')
        nombre = request.POST.get('nombre')
        proveedor = request.POST.get('proveedor')
        precio = request.POST.get('precio')
        stock = request.POST.get('stock')
        estado = request.POST.get('estado')
        imagen = request.FILES.get('imagen')
        try:
            if int(precio) <= 0:
                return JsonResponse({'status': 'error', 'msg': 'El precio debe ser mayor a 0'})
            producto = Producto.objects.get(pk=id)
            producto.nombre = nombre
            producto.proveedor = proveedor
            producto.precio = int(precio)
            producto.stock = int(stock)
            producto.estado = estado
            if imagen:
                # Validar formato
                if not imagen.content_type in ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']:
                    return JsonResponse({'status': 'error', 'msg': 'Formato de imagen no permitido'})
                producto.imagen = imagen
            producto.save()
            registrar_log(request.user.username if request.user.is_authenticated else None, 'editar', 'Producto', f'ID: {id}, Nombre: {nombre}, Precio: {precio}, Stock: {stock}, Estado: {estado}')
            imagen_url = producto.imagen.url if producto.imagen else None
            return JsonResponse({'status': 'ok', 'imagen_url': imagen_url})
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
    id = request.POST.get('id')
    if not id:
        return JsonResponse({'status': 'error', 'msg': 'ID de producto requerido'})
    try:
        producto = Producto.objects.get(pk=id)
        # Guardar detalles antes de eliminar
        detalles = f"ID: {producto.id}, Nombre: {producto.nombre}, Precio: {producto.precio}"
        registrar_log(request.user.username if request.user.is_authenticated else None, 'eliminar', 'Producto', detalles)
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
    descripcion = request.POST.get('descripcion')
    imagen = request.FILES.get('imagen')
    if not (nombre  and precio and stock):
        return JsonResponse({'status': 'error', 'msg': 'Faltan campos obligatorios'})
    try:
        if int(precio) <= 0:
            return JsonResponse({'status': 'error', 'msg': 'El precio debe ser mayor a 0'})
    except Exception:
        return JsonResponse({'status': 'error', 'msg': 'Precio inválido'})
    from .models import Producto
    if Producto.objects.filter(nombre=nombre).exists():
        return JsonResponse({'status': 'error', 'msg': 'Ya existe un producto con ese nombre'})
    try:
        # Validar formato de imagen si se sube
        if imagen and imagen.content_type not in ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']:
            return JsonResponse({'status': 'error', 'msg': 'Formato de imagen no permitido'})
        producto = Producto.objects.create(
            nombre=nombre,
            proveedor=proveedor,
            precio=int(precio),
            stock=int(stock),
            estado=estado,
            descripcion=descripcion,
            imagen=imagen if imagen else 'imgProductos/placeholder.png'
        )
        registrar_log(request.user.username if request.user.is_authenticated else None, 'crear', 'Producto', f'Nombre: {nombre}, Precio: {precio}, Stock: {stock}, Estado: {estado}')
        return JsonResponse({'status': 'ok', 'id': producto.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@csrf_exempt
@require_POST
def eliminar_masivo_producto(request):
    """API para eliminar productos de forma masiva desde el dashboard admin."""
    ids = request.POST.get('ids', '')
    id_list = [int(i) for i in ids.split(',') if i.isdigit()]
    if not id_list:
        return JsonResponse({'status': 'error', 'msg': 'No se recibieron IDs válidos'})
    try:
        productos = Producto.objects.filter(id__in=id_list)
        for producto in productos:
            detalles = f"ID: {producto.id}, Nombre: {producto.nombre}, Precio: {producto.precio}"
            registrar_log(request.user.username if request.user.is_authenticated else None, 'eliminar', 'Producto', detalles)
        productos.delete()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@require_GET
def api_logs(request):
    """Devuelve logs de auditoría filtrados para el dashboard."""
    usuario = request.GET.get('usuario', '').strip()
    accion = request.GET.get('accion', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    if usuario:
        logs = logs.filter(usuario__icontains=usuario)
    if accion:
        logs = logs.filter(accion=accion)
    if fecha_desde:
        logs = logs.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        logs = logs.filter(fecha_hora__date__lte=fecha_hasta)
    logs = logs.order_by('-fecha_hora')[:200]  # Limitar a 200 más recientes
    data = [{
        'fecha_hora': l.fecha_hora.strftime('%Y-%m-%d %H:%M:%S'),
        'usuario': l.usuario,
        'accion': l.accion,
        'modelo': l.modelo,
        'detalles': l.detalles,
    } for l in logs]
    return JsonResponse({'logs': data})

@require_GET
def api_pedidos(request):
    """Devuelve lista de pedidos/ventas con filtros."""
    usuario = request.GET.get('usuario', '').strip()
    estado = request.GET.get('estado', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    pedidos = Pedido.objects.all()
    if usuario:
        pedidos = pedidos.filter(usuario__username__icontains=usuario)
    if estado:
        pedidos = pedidos.filter(estado=estado)
    if fecha_desde:
        pedidos = pedidos.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        pedidos = pedidos.filter(fecha__date__lte=fecha_hasta)
    pedidos = pedidos.order_by('-fecha')[:200]
    data = []
    for p in pedidos:
        items = list(p.items.values('producto__nombre', 'cantidad', 'precio_unitario'))
        data.append({
            'id': p.id,
            'fecha': p.fecha.strftime('%Y-%m-%d %H:%M'),
            'usuario': p.usuario.username if p.usuario else '',
            'tipo': p.get_tipo_display(),
            'estado': p.get_estado_display(),
            'total': float(p.total),
            'items': items,
        })
    return JsonResponse({'pedidos': data})

@csrf_exempt
@require_POST
def api_pedido_nuevo(request):
    """Crea un nuevo pedido o venta."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        usuario_id = data.get('usuario_id')
        usuario_obj = None
        if usuario_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            usuario_obj = User.objects.get(id=usuario_id)
        pedido = Pedido.objects.create(
            usuario=usuario_obj,
            tipo=data.get('tipo', 'pedido'),
            estado=data.get('estado', 'pendiente'),
            total=data.get('total', 0),
            observaciones=data.get('observaciones', '')
        )
        for item in data['items']:
            PedidoItem.objects.create(
                pedido=pedido,
                producto_id=item['producto_id'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario']
            )
        return JsonResponse({'status': 'ok', 'id': pedido.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)})

@csrf_exempt
@require_GET
def api_clientes_distribuidores(request):
    """Devuelve lista de clientes y distribuidores con filtros opcionales."""
    tipo = request.GET.get('tipo', '').strip()
    nombre = request.GET.get('nombre', '').strip()
    activos = request.GET.get('activos', '1')
    qs = ClienteDistribuidor.objects.all()
    if tipo in ['usuario', 'distribuidor']:
        qs = qs.filter(tipo=tipo)
    if nombre:
        qs = qs.filter(nombre__icontains=nombre)
    if activos == '1':
        qs = qs.filter(activo=True)
    qs = qs.order_by('-fecha_creacion')[:200]
    data = []
    for c in qs:
        data.append({
            'id': c.id,
            'tipo': c.get_tipo_display(),
            'nombre': c.nombre,
            'rut': c.rut,
            'email': c.email,
            'telefono': c.telefono,
            'direccion': c.direccion,
            'fecha_creacion': c.fecha_creacion.strftime('%Y-%m-%d'),
            'activo': c.activo,
        })
    return JsonResponse({'clientes': data})

@csrf_exempt
@require_POST
def api_nuevo_cliente_distribuidor(request):
    """Crea un nuevo cliente o distribuidor. Si es distribuidor y se solicita, crea usuario Django asociado."""
    data = json.loads(request.body)
    tipo = data.get('tipo', 'usuario')
    nombre = data.get('nombre', '').strip()
    rut = data.get('rut', '').strip()
    email = data.get('email', '').strip()
    telefono = data.get('telefono', '').strip()
    direccion = data.get('direccion', '').strip()
    crear_usuario = data.get('crear_usuario_distribuidor', False)
    password = data.get('password_distribuidor', '').strip()
    if not nombre:
        return JsonResponse({'status': 'error', 'msg': 'El nombre es obligatorio'})
    # Crear ClienteDistribuidor
    obj = ClienteDistribuidor.objects.create(
        tipo=tipo,
        nombre=nombre,
        rut=rut,
        email=email,
        telefono=telefono,
        direccion=direccion,
        activo=True
    )
    usuario_creado = None
    usuario_error = None
    if tipo == 'distribuidor' and crear_usuario and email and password:
        from .models import Usuario
        if Usuario.objects.filter(email=email).exists():
            usuario_error = 'Ya existe un usuario con ese email.'
        else:
            try:
                usuario = Usuario.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    rut=rut or None,
                    telefono=telefono or None,
                    direccion=direccion or None,
                )
                usuario.first_name = nombre
                usuario.save()
                usuario_creado = usuario.username
            except Exception as e:
                usuario_error = str(e)
    resp = {'status': 'ok', 'id': obj.id}
    if usuario_creado:
        resp['usuario_creado'] = usuario_creado
        resp['password'] = password
    if usuario_error:
        resp['usuario_error'] = usuario_error
    return JsonResponse(resp)

@csrf_exempt
@require_GET
def api_dashboard_resumen(request):
    total_productos = Producto.objects.count()
    total_pedidos = Pedido.objects.count()
    total_clientes = ClienteDistribuidor.objects.filter(tipo='usuario').count()
    stock_bajo = Producto.objects.filter(stock__lt=10).count()
    return JsonResponse({
        'total_productos': total_productos,
        'total_pedidos': total_pedidos,
        'total_clientes': total_clientes,
        'stock_bajo': stock_bajo,
    })

@csrf_exempt
@require_POST
def terminar_pedido(request, pedido_id):
    from .models import Pedido
    try:
        pedido = Pedido.objects.get(id=pedido_id)
        pedido.estado = 'entregado'
        pedido.save()
        return JsonResponse({'status': 'ok'})
    except Pedido.DoesNotExist:
        return JsonResponse({'status': 'error', 'msg': 'Pedido no encontrado'})

@csrf_exempt
@require_POST
def eliminar_pedido(request, pedido_id):
    from .models import Pedido
    try:
        pedido = Pedido.objects.get(id=pedido_id)
        pedido.delete()
        return JsonResponse({'status': 'ok'})
    except Pedido.DoesNotExist:
        return JsonResponse({'status': 'error', 'msg': 'Pedido no encontrado'})



