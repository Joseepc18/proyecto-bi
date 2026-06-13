import json
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

FUENTE = "computrabajo"
BASE = "https://ec.computrabajo.com/trabajo-de-"
# Roles objetivo del proyecto, tal como aparecen en la URL de Computrabajo.
ROLES = ["desarrollador", "analista-de-datos", "qa"]
# Tope de seguridad para no quedar en un bucle infinito.
MAX_PAGINAS = 20
DIR_RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / FUENTE

# Sin un User-Agent de navegador, muchos sitios rechazan la peticion.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _texto(elemento):
    # Devuelve el texto limpio del elemento, o None si no existe.
    return elemento.get_text(" ", strip=True) if elemento else None


def _parsear_pagina(soup, rol):
    # Extrae las ofertas de una sola pagina de listado (sin la descripcion).
    ofertas = []
    for art in soup.select("article.box_offer"):
        titulo = art.select_one("a.js-o-link")

        # Salario y modalidad estan en el mismo bloque; los separamos por el "$".
        salario, modalidad = None, None
        for span in art.select("div.fs13.mt15 span.dIB.mr10"):
            texto = span.get_text(strip=True)
            if "$" in texto:
                salario = texto
            else:
                modalidad = texto

        ofertas.append({
            "rol_busqueda": rol,
            "titulo": _texto(titulo),
            "empresa": _texto(art.select_one("a.t_ellipsis")),
            # :not(.dFlex) evita confundir la ubicacion con el rating de la empresa.
            "ubicacion": _texto(art.select_one("p.fs16.fc_base.mt5:not(.dFlex) span.mr10")),
            "salario": salario,
            "modalidad": modalidad,
            "fecha": _texto(art.select_one("p.fs13.fc_aux.mt15")),
            "link": "https://ec.computrabajo.com" + titulo["href"] if titulo else None,
        })
    return ofertas


def extraer_descripcion(link):
    # Entra a la pagina de la oferta y devuelve el texto completo de la descripcion.
    respuesta = requests.get(link, headers=HEADERS, timeout=20)
    respuesta.raise_for_status()
    soup = BeautifulSoup(respuesta.text, "html.parser")
    return _texto(soup.select_one("div.mb40.pb40.bb1"))


def extraer_ofertas():
    ofertas = []
    # Por cada rol objetivo, recorremos sus paginas hasta que una venga vacia.
    for rol in ROLES:
        for pagina in range(1, MAX_PAGINAS + 1):
            url = f"{BASE}{rol}" if pagina == 1 else f"{BASE}{rol}?p={pagina}"
            respuesta = requests.get(url, headers=HEADERS, timeout=20)
            respuesta.raise_for_status()
            soup = BeautifulSoup(respuesta.text, "html.parser")

            nuevas = _parsear_pagina(soup, rol)
            if not nuevas:        # pagina sin ofertas = ya no hay mas para este rol
                break

            # Entramos a cada oferta a traer su descripcion completa.
            for oferta in nuevas:
                try:
                    oferta["descripcion"] = (
                        extraer_descripcion(oferta["link"]) if oferta["link"] else None
                    )
                except requests.RequestException:
                    # Si esa pagina falla, seguimos con las demas sin cortar todo.
                    oferta["descripcion"] = None
                time.sleep(1)     # pausa entre cada detalle (rate limiting)

            ofertas.extend(nuevas)
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