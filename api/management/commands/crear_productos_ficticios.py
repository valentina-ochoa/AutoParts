from django.core.management.base import BaseCommand
from django.utils.text import slugify
from api.models import Producto
import random
import uuid
from faker import Faker

fake = Faker('es_ES')

productos_por_categoria = {
    "Motores y Componentes": ["Filtro de aceite", "Filtro de aire", "Bujía", "Correa de distribución"],
    "Frenos y Suspensión": ["Pastilla de freno", "Disco de freno", "Amortiguador", "Rótula"],
    "Electricidad y Baterías": ["Alternador", "Batería", "Luz y faro", "Sensor y fusible"],
    "Accesorios y Seguridad": ["Alarma", "Cinturón de seguridad", "Cubre asiento", "Kit de emergencia"]
}

class Command(BaseCommand):
    help = 'Genera productos ficticios en la base de datos'

    def add_arguments(self, parser):
        parser.add_argument('cantidad', type=int, help='Número de productos a crear')

    def handle(self, *args, **kwargs):
        cantidad = kwargs['cantidad']
        for _ in range(cantidad):
            categoria = random.choice(list(productos_por_categoria.keys()))
            nombre_base = random.choice(productos_por_categoria[categoria])
            nombre = f"{nombre_base} {fake.word().capitalize()} {random.randint(100,999)}"

            producto = Producto(
                codigo_producto=str(uuid.uuid4())[:8],
                marca=fake.company(),
                codigo_interno=f"INT-{random.randint(1000, 9999)}",
                nombre=nombre,
                stock=random.randint(0, 150),
                imagen="imgProductos/placeholder.jpg",
                descripcion=fake.sentence(nb_words=12),
                precio=random.randint(5000, 100000),
                etiquetas=", ".join(fake.words(nb=3)),
                estado="activo",
                proveedor=fake.company(),
                slug=slugify(nombre)
            )
            producto.save()

        self.stdout.write(self.style.SUCCESS(f"Se crearon {cantidad} productos ficticios correctamente."))
