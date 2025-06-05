from django import template
from api.models import ClienteDistribuidor

register = template.Library()

@register.filter
def is_distribuidor(user):
    if not user.is_authenticated or not user.email:
        return False
    return ClienteDistribuidor.objects.filter(email=user.email, tipo='distribuidor', activo=True).exists()
