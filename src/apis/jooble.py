import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

FUENTE = "jooble"
# Carpeta data/raw/jooble/ calculada desde la ubicacion de este archivo.
DIR_RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / FUENTE

# Carga el .env y saca la API key (no se escribe en el codigo).
load_dotenv()
API_KEY = os.getenv("JOOBLE_API_KEY")


def consultar_ofertas(keyword, ubicacion=""):
    # Si falta la clave, corta con un mensaje claro en vez de fallar despues.
    if not API_KEY:
        raise RuntimeError("Falta JOOBLE_API_KEY en el archivo .env")

    # ubicacion vacia = busqueda internacional (Jooble no indexa empleos de Ecuador).
    url = f"https://jooble.org/api/{API_KEY}"
    cuerpo = {"keywords": keyword, "location": ubicacion}
    # POST con timeout: si la API no responde en 30s, corta en vez de colgarse.
    respuesta = requests.post(url, json=cuerpo, timeout=30)
    # Si el servidor respondio con error (404, 500, ...), lanza una excepcion.
    respuesta.raise_for_status()
    datos = respuesta.json()
    # La API envuelve las ofertas dentro de la clave "jobs".
    return datos["jobs"]


def guardar_raw(ofertas):
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
    ofertas = consultar_ofertas("developer")
    destino = guardar_raw(ofertas)
    print(f"[{FUENTE}] {len(ofertas)} ofertas guardadas en {destino}")