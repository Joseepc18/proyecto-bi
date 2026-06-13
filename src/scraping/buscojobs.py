import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

FUENTE = "buscojobs"
# Listado de la categoria "Tecnologia de la informacion" (ts1017) del portal ecuatoriano.
BASE = "https://www.buscojobs.com.ec/ofertas/ts1017/trabajo-de-tecnologia-de-la-informacion"
# Tope de seguridad para no quedar en un bucle infinito.
MAX_PAGINAS = 30
DIR_RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / FUENTE

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _nombre(dic):
    # Ciudad/Departamento/Pais vienen como diccionarios; sacamos su "Nombre".
    return dic.get("Nombre") if isinstance(dic, dict) else None


def _modalidad(oferta):
    # El JSON no trae un texto de modalidad; lo deducimos de sus flags.
    if oferta.get("PermiteTeletrabajo"):
        return "Remoto"
    if oferta.get("PermiteTrabajoHibrido"):
        return "Hibrido"
    return "Presencial"


def _link(oferta):
    # El link se arma con el titulo convertido a slug + el id de la oferta.
    slug = re.sub(r"[^a-z0-9]+", "-", oferta["CargoVacante"].lower()).strip("-")
    return f"https://www.buscojobs.com.ec/{slug}-ID-{oferta['IdOferta']}"


def _oferta_limpia(o):
    # Toma una oferta cruda del JSON y deja solo los campos que nos interesan.
    ubicacion = ", ".join(
        n for n in [_nombre(o.get("Ciudad")), _nombre(o.get("Departamento"))] if n
    )
    return {
        "titulo": o.get("CargoVacante"),
        "empresa": o.get("NombreEmpresa"),
        "ubicacion": ubicacion or _nombre(o.get("Pais")),
        "salario": None,                 # el listado no expone salario
        "modalidad": _modalidad(o),
        "fecha": o.get("FechaInicio"),
        "descripcion": o.get("Descripcion"),
        "link": _link(o),
    }


def _ofertas_de_pagina(pagina):
    # Descarga una pagina y saca las ofertas del JSON incrustado __NEXT_DATA__.
    url = BASE if pagina == 1 else f"{BASE}/{pagina}"
    respuesta = requests.get(url, headers=HEADERS, timeout=20)
    respuesta.raise_for_status()
    soup = BeautifulSoup(respuesta.text, "html.parser")
    datos = json.loads(soup.find("script", id="__NEXT_DATA__").string)
    return datos["props"]["pageProps"]["resultadosIniciales"]["ofertas"]


def extraer_ofertas():
    ofertas = []
    # Paginamos (/2, /3, ...) hasta que una pagina venga sin ofertas.
    for pagina in range(1, MAX_PAGINAS + 1):
        crudas = _ofertas_de_pagina(pagina)
        if not crudas:
            break
        ofertas.extend(_oferta_limpia(o) for o in crudas)
        time.sleep(1)         # pausa para no saturar el servidor (rate limiting)
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
