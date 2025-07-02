from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario
import phonenumbers
from itertools import cycle

class RegistroUsuarioForm(UserCreationForm):
    rut = forms.CharField(max_length=12, required=True)
    first_name = forms.CharField(max_length=150, required=True, label="Nombre")
    last_name = forms.CharField(max_length=150, required=True, label="Apellido")
    telefono = forms.CharField(max_length=15, required=True, help_text="Incluye el código de país, por ejemplo: +56912345678")
    direccion = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Dirección completa'}),
        label="Dirección",
        help_text="Ejemplo: Av. Apoquindo 3000, Las Condes, Santiago, Región Metropolitana"
    )
    fecha_nacimiento = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Fecha de Nacimiento"
    )
    class Meta:
        model = Usuario
        fields = (
            "username", "email", "rut", "first_name", "last_name",  "telefono",
            "direccion", "fecha_nacimiento", "password1", "password2"
        )
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['email'].label = 'Correo Electrónico'
        self.fields['rut'].widget.attrs['placeholder'] = 'RUT (sin puntos ni guión)'

    def clean_username(self):
        username = self.cleaned_data["username"].lower()
        if Usuario.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username