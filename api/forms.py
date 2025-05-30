from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario
import phonenumbers
from itertools import cycle

class RegistroUsuarioForm(UserCreationForm):
    rut = forms.CharField(max_length=12, required=False)
    telefono = forms.CharField(max_length=15, required=False, help_text="Incluye el código de país, por ejemplo: +56912345678")

    class Meta:
        model = Usuario
        fields = ("username", "email", "rut", "telefono", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_rut(self):
        rut = self.cleaned_data.get('rut', '').upper().replace("-", "").replace(".", "")
        if not rut:
            return rut
        rut_aux = rut[:-1]
        dv = rut[-1:]

        if not rut_aux.isdigit() or not (1_000_000 <= int(rut_aux) <= 25_000_000):
            raise forms.ValidationError("RUT fuera de rango o con formato incorrecto.")

        revertido = map(int, reversed(rut_aux))
        factors = cycle(range(2, 8))
        suma = sum(d * f for d, f in zip(revertido, factors))
        residuo = suma % 11

        if dv == 'K':
            if residuo != 1:
                raise forms.ValidationError("RUT inválido.")
        elif dv == '0':
            if residuo != 0:
                raise forms.ValidationError("RUT inválido.")
        else:
            if residuo != 11 - int(dv):
                raise forms.ValidationError("RUT inválido.")
        return rut

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '')
        if not telefono:
            return telefono
        try:
            phone = phonenumbers.parse(telefono, None)
            if not phonenumbers.is_valid_number(phone):
                raise forms.ValidationError("Número de teléfono inválido.")
        except Exception:
            raise forms.ValidationError("Número de teléfono inválido.")
        return phonenumbers.format_number(phone, phonenumbers.PhoneNumberFormat.E164)