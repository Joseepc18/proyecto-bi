import json
import sys
from datetime import datetime
from pathlib import Path

import requests

# Permite importar utils_log estando en src/apis (sube a src/).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils_log import registrar_error

FUENTE = "remotive"
URL_API = "https://remotive.com/api/remote-jobs"
# Carpeta data/raw/remotive/ calculada desde la ubicacion de este archivo.
DIR_RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / FUENTE

# Categorias de Remotive que nos interesan (campo "category" de cada oferta).
# La API a veces ignora el parametro y devuelve otras categorias (Sales, Writing...),
# por eso filtramos del lado del codigo en vez de confiar solo en el parametro.
CATEGORIAS_TECH = {"Software Development", "Data and Analytics", "Artificial Intelligence"}


def consultar_ofertas(categoria="software-dev"):
    parametros = {"category": categoria}
    # timeout: si la API no responde en 30s, corta y lanza error en vez de colgarse.
    respuesta = requests.get(URL_API, params=parametros, timeout=30)
    # Si el servidor respondio con error (404, 500, ...), lanza una excepcion.
    respuesta.raise_for_status()
    datos = respuesta.json()
    # La API envuelve las ofertas dentro de la clave "jobs".
    ofertas = datos["jobs"]
    # Nos quedamos solo con las categorias tech (la API no garantiza el filtro).
    return [o for o in ofertas if o.get("category") in CATEGORIAS_TECH]


def guardar_raw(ofertas):
    # Crea la carpeta si no existe (no falla si ya existe).
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    # Nomenclatura Raw exigida: fuente_YYYY-MM-DD.json
    fecha = datetime.now().strftime("%Y-%m-%d")
    ruta = DIR_RAW / f"{FUENTE}_{fecha}.json"
    # ensure_ascii=False para conservar tildes/ñ; indent=2 para que sea legible.
    ruta.write_text(
        json.dumps(ofertas, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ruta


if __name__ == "__main__":
    # Consultamos software y datos; deduplicamos por id (la API repite ofertas entre categorias).
    ofertas, vistos = [], set()
    for categoria in ("software-dev", "data"):
        try:
            resultado = consultar_ofertas(categoria)
        except (requests.RequestException, KeyError) as e:
            registrar_error(
                FUENTE, "consulta_api_fallida",
                f"Fallo la categoria '{categoria}': {e}",
                "se omite esa categoria y se continua",
            )
            continue
        for o in resultado:
            if o.get("id") not in vistos:
                vistos.add(o.get("id"))
                ofertas.append(o)
    destino = guardar_raw(ofertas)
    print(f"[{FUENTE}] {len(ofertas)} ofertas guardadas en {destino}")