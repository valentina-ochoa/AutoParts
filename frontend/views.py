from django.http import JsonResponse
from django.shortcuts import render, redirect
from api.forms import RegistroUsuarioForm
from api_externa.repuestos import obtener_repuestos
from api_externa.repuestos import obtener_repuestos_local
from django.views.decorators.csrf import csrf_exempt


def index(request):
    return render(request, 'pages/index.html')

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
    if request.method == "POST":
        producto = {
            "codigo": request.POST.get("codigo_producto"),
            "nombre": request.POST.get("nombre"),
            "precio": int(request.POST.get("precio"))
        }

        carrito = request.session.get("carrito_externo", [])
        carrito.append(producto)
        request.session["carrito_externo"] = carrito

        # 
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "ok"})

        return redirect('carrito')

    carrito = request.session.get("carrito_externo", [])
    total = sum([item["precio"] for item in carrito])
    context = {
        "items": [{"producto": item, "cantidad": 1} for item in carrito],
        "total": total,
        "total_usd": round(total / 900, 2)
    }
    return render(request, 'pages/carrito.html', context)


def catalogo_externo(request):
    repuestos = obtener_repuestos()
    return render(request, "pages/catalogo_externo.html", {"repuestos": repuestos})




def catalogo_externo(request):
    repuestos = obtener_repuestos_local()
    print("REPS DESDE API →", repuestos) 
    return render(request, "pages/catalogo_externo.html", {"repuestos": repuestos})

from django.shortcuts import redirect

def limpiar_carrito(request):
    if "carrito_externo" in request.session:
        del request.session["carrito_externo"]
    return redirect('carrito') 

def pago_exito(request):
    return render(request, 'pages/pago_exito.html')

from django.shortcuts import redirect



def limpiar_carrito_y_volver_inicio(request):
    if "carrito" in request.session:
        del request.session["carrito"]
        request.session.modified = True
    elif "carrito_externo" in request.session:
        del request.session["carrito_externo"]
        request.session.modified = True
    return redirect('home')  # Asegúrate que este sea el nombre de la ruta al inicio




