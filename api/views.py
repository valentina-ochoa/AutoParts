from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .forms import RegistroUsuarioForm
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages

from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType


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
    # Obtener productos desde el carrito (usando sesión)
    carrito = request.session.get("carrito_externo", [])

    if not carrito:
        messages.error(request, "Tu carrito está vacío.")
        return redirect('/carrito/')

    # Calcular el monto total en CLP
    monto_clp = sum(item['precio'] for item in carrito)

    # Datos para Transbank
    buy_order = "ORDEN123"  # puedes usar uuid.uuid4() si deseas que sea único
    session_id = "SESSION123"
    return_url = request.build_absolute_uri(reverse('pago_exito'))

    transaction = Transaction(WebpayOptions(
        commerce_code=settings.TRANSBANK_COMMERCE_CODE,
        api_key=settings.TRANSBANK_API_KEY,
        integration_type=IntegrationType.TEST
    ))

    try:
        response = transaction.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=int(monto_clp),  # asegúrate de que sea int
            return_url=return_url
        )
        return redirect(f"{response['url']}?token_ws={response['token']}")
    except Exception as e:
        messages.error(request, f'Error al iniciar el pago: {str(e)}')
        return redirect('/carrito/')




def confirmar_pago(request):
    token = request.GET.get("token_ws")
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
        if response['status'] == 'AUTHORIZED':
            cart = get_or_create_cart(request)
            if cart:
                cart.items.all().delete()
            messages.success(request, "Pago exitoso.")
        else:
            messages.error(request, f"Pago fallido: {response['status']}")
    except Exception as e:
        messages.error(request, f"Error al confirmar pago: {str(e)}")
    return redirect("carrito")

def pago_exito(request):
    return render(request, "pages/pago_exito.html")

from .models import Carrito 

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Carrito.objects.get_or_create(usuario=request.user)
        cart.total_calculado = cart.total()
        cart.total_usd_calculado = round(cart.total_calculado / 850, 2)  
        return cart
    return None


from api_externa.repuestos import obtener_repuestos



