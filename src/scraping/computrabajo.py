import json
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

FUENTE = "computrabajo"
URL = "https://ec.computrabajo.com/empleos-de-tecnologia-sistemas-y-telecomunicaciones"
# Carpeta data/raw/computrabajo/ calculada desde la ubicacion de este archivo.
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
    return elemento.get_text(strip=True) if elemento else None


def extraer_ofertas():
    respuesta = requests.get(URL, headers=HEADERS, timeout=20)
    respuesta.raise_for_status()
    soup = BeautifulSoup(respuesta.text, "html.parser")

    ofertas = []
    # Cada oferta es un <article class="box_offer">.
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
