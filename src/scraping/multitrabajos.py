import json
import time
from datetime import datetime
from pathlib import Path

import requests

FUENTE = "multitrabajos"
# API interna del portal, descubierta inspeccionando el trafico de la web (es una SPA).
URL_API = "https://www.multitrabajos.com/api/avisos/searchV2"
AREA = "tecnologia-sistemas-y-telecomunicaciones"
# Tope de seguridad para no quedar en un bucle infinito.
MAX_PAGINAS = 30
DIR_RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / FUENTE

# x-site-id identifica el portal (BMEC = Bumeran Ecuador); sin el, la API rechaza.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json",
    "x-site-id": "BMEC",
    "Referer": (
        "https://www.multitrabajos.com/"
        "empleos-area-tecnologia-sistemas-y-telecomunicaciones.html"
    ),
}


def _aviso_a_oferta(aviso):
    # Toma un aviso crudo de la API y deja solo los campos que nos interesan.
    return {
        "titulo": aviso.get("titulo"),
        "empresa": aviso.get("empresa"),
        "ubicacion": aviso.get("localizacion"),
        "salario": None,                       # la API del listado no expone salario
        "modalidad": aviso.get("modalidadTrabajo"),
        "tipo_trabajo": aviso.get("tipoTrabajo"),
        "fecha": aviso.get("fechaPublicacion"),
        "descripcion": aviso.get("detalle"),
        "link": f"https://www.multitrabajos.com/empleos/aviso-{aviso.get('id')}.html",
    }


def extraer_ofertas():
    ofertas = []
    body = {"filtros": [{"id": "area", "value": AREA}]}
    # La API pagina con page=0,1,2...; paramos cuando una pagina viene vacia.
    for pagina in range(MAX_PAGINAS):
        params = {"pageSize": 20, "page": pagina, "sort": "RELEVANTES"}
        respuesta = requests.post(URL_API, headers=HEADERS, params=params, json=body, timeout=20)
        respuesta.raise_for_status()
        avisos = respuesta.json().get("content", [])
        if not avisos:        # pagina vacia = ya no hay mas ofertas
            break
        ofertas.extend(_aviso_a_oferta(a) for a in avisos)
        time.sleep(1)         # pausa para no saturar la API (rate limiting)
    return ofertas


def guardar_raw(ofertas):
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%d-%m-%Y")
    ruta = DIR_RAW / f"{fecha}.json"
    ruta.write_text(
        json.dumps(ofertas, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ruta


if __name__ == "__main__":
    ofertas = extraer_ofertas()
    destino = guardar_raw(ofertas)
    print(f"[{FUENTE}] {len(ofertas)} ofertas guardadas en {destino}")
