"""
Conector de la API de Remotive (remotive.com/api/remote-jobs).

Descarga ofertas remotas de TI (sin autenticacion) y guarda el resultado
CRUDO en data/raw/remotive/<fecha>.json. Esta es la etapa RAW: no se limpia
ni transforma nada, solo se trae y se guarda tal cual.
"""

import json
from datetime import datetime
from pathlib import Path

import requests

FUENTE = "remotive"
URL_API = "https://remotive.com/api/remote-jobs"
# Carpeta data/raw/remotive/ calculada desde la ubicacion de este archivo.
DIR_RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / FUENTE


def consultar_ofertas(categoria="software-dev"):
    """Pide a la API de Remotive las ofertas de una categoria.

    Parametros:
        categoria: slug de Remotive (ej. "software-dev", "data").
    Retorna:
        Lista de ofertas (cada una es un diccionario) tal como las da la API.
    """
    parametros = {"category": categoria}
    # timeout: si la API no responde en 30s, corta y lanza error en vez de colgarse.
    respuesta = requests.get(URL_API, params=parametros, timeout=30)
    # Si el servidor respondio con error (404, 500, ...), lanza una excepcion.
    respuesta.raise_for_status()
    datos = respuesta.json()
    # La API envuelve las ofertas dentro de la clave "jobs".
    return datos["jobs"]


def guardar_raw(ofertas):
    """Guarda las ofertas crudas en data/raw/remotive/<fecha>.json."""
    # Crea la carpeta si no existe (no falla si ya existe).
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%d-%m-%Y")
    ruta = DIR_RAW / f"{fecha}.json"
    # ensure_ascii=False para conservar tildes/ñ; indent=2 para que sea legible.
    ruta.write_text(
        json.dumps(ofertas, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ruta


if __name__ == "__main__":
    ofertas = consultar_ofertas("software-dev")
    destino = guardar_raw(ofertas)
    print(f"[{FUENTE}] {len(ofertas)} ofertas guardadas en {destino}")
