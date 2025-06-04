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



# Las siguientes funciones han sido migradas a api/views.py y deben ser consumidas solo vía API.
# Se mantienen aquí solo como referencia temporal y serán eliminadas próximamente.
# from api.views import agregar_al_carrito, eliminar_del_carrito, actualizar_cantidad_carrito, carrito_view, limpiar_carrito, limpiar_carrito_y_volver_inicio

# @csrf_exempt
# @require_POST
# def actualizar_cantidad_carrito(request):
#     pass

# @csrf_exempt
# @require_POST
# def eliminar_del_carrito(request, item_id):
#     pass

# @csrf_exempt
# @require_POST
# def agregar_al_carrito(request):
#     pass

# @csrf_exempt
# def carrito_view(request):
#     pass

# def limpiar_carrito(request):
#     pass

# def limpiar_carrito_y_volver_inicio(request):
#     pass

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

#Iniciar pago
#@csrf_exempt
#def iniciar_pago(request):
#    print("Entrando a iniciar_pago")
#    if request.method == 'POST':
#        print("Método POST recibido")
#        # Obtén el total del carrito (ajusta según tu lógica)
#        if request.user.is_authenticated:
#            print("Usuario autenticado")
#            try:
#                carrito = Carrito.objects.get(usuario=request.user)
#                total = carrito.total()
#                print(f"Total carrito usuario: {total}")
#            except Carrito.DoesNotExist:
#                print("No existe carrito para usuario")
#                total = 0
#        else:
#            print("Usuario no autenticado, usando cookie")
#            carrito_cookie = request.COOKIES.get('carrito')
#            total = 0
#            if carrito_cookie:
#                try:
#                    carrito_data = json.loads(carrito_cookie)
#                    for item in carrito_data.values():
#                        try:
#                            producto = Producto.objects.get(pk=item['producto_id'])
#                            cantidad = item['cantidad']
#                            subtotal = producto.precio * cantidad
#                            total += subtotal
#                        except Producto.DoesNotExist:
#                            print(f"Producto {item['producto_id']} no existe")
#                            continue
#                except Exception as e:
#                    print(f"Error leyendo cookie carrito: {e}")
#                    total = 0
#            print(f"Total carrito cookie: {total}")
#
#        # Datos para Transbank
#        buy_order = f"ORDER-{request.user.id if request.user.is_authenticated else 'anon'}-{Carrito.objects.count()}"
#        session_id = str(request.user.id) if request.user.is_authenticated else request.session.session_key or "anon"
#        amount = int(total)
#        return_url = request.build_absolute_uri('/pago/exito/')
#        print(f"Creando transacción Transbank: buy_order={buy_order}, session_id={session_id}, amount={amount}, return_url={return_url}")
#
#        # Configura Transbank en modo integración
#        tx = Transaction(IntegrationType.TEST)
#        response = tx.create(buy_order, session_id, amount, return_url)
#        print(f"Respuesta Transbank: {response}")
#
#        # Redirige al usuario a Webpay
#        url = response['url']
#        token = response['token']
#        print(f"Redirigiendo a Webpay: url={url}, token={token}")
#        return render(request, 'pages/redirect_webpay.html', {'url': url, 'token': token})
#
#    print("Método GET, mostrando iniciar_pago.html")
#    return render(request, 'pages/iniciar_pago.html')

#def pago_cancelado(request):
#    return render(request, 'pages/pago_cancelado.html')

#@csrf_exempt
#def pago_exito(request):
#    token = request.POST.get('token_ws')
#    if not token:
#        # No hay token, el usuario canceló o falló el pago
#        return redirect('pago_cancelado')
#
#    try:
#        tx = Transaction()
#        response = tx.commit(token)
#        if response['status'] == 'AUTHORIZED':
#            # Pago exitoso
#            return render(request, 'pages/pago_exito.html', {'response': response})
#        else:
#            # Pago rechazado o fallido
#            return redirect('pago_cancelado')
#    except Exception as e:
#        # Error en la confirmación
#        return redirect('pago_cancelado')



