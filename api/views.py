from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .forms import RegistroUsuarioForm


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