# api_externa/repuestos.py
import requests

def obtener_repuestos():
    url = "https://example.com/api/repuestos"  # simulado
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Error consultando API externa: {e}")
        return []

import json
import os

def obtener_repuestos_local():
    ruta = os.path.join(os.path.dirname(__file__), 'repuestos.json')
    with open(ruta, 'r', encoding='utf-8') as archivo:
        return json.load(archivo)
