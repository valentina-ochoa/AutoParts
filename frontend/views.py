from django.shortcuts import render, redirect
from api.forms import RegistroUsuarioForm

# Create your views here.

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