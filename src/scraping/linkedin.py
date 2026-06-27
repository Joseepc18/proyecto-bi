import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Permite importar utils_log estando en src/scraping (sube a src/).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils_log import registrar_error

FUENTE = "linkedin"
# Endpoint publico de busqueda de empleos de LinkedIn (sin login).
URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
# Roles objetivo del proyecto.
ROLES = ["desarrollador", "analista de datos", "qa"]
UBICACION = "Ecuador"
# El endpoint devuelve 10 ofertas por peticion; avanzamos de 10 en 10.
PASO = 10
MAX_OFERTAS_POR_ROL = 200
DIR_RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / FUENTE

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _texto(elemento):
    return elemento.get_text(strip=True) if elemento else None


def _parsear(html, rol):
    soup = BeautifulSoup(html, "html.parser")
    ofertas = []
    for card in soup.select("div.base-card"):
        titulo = card.select_one("h3.base-search-card__title")
        if not titulo:
            continue
        fecha = card.select_one("time")
        enlace = card.select_one("a.base-card__full-link")
        ofertas.append({
            "rol_busqueda": rol,
            "titulo": _texto(titulo),
            "empresa": _texto(card.select_one("h4.base-search-card__subtitle")),
            "ubicacion": _texto(card.select_one("span.job-search-card__location")),
            "salario": None,              # el listado no expone salario
            "fecha": fecha.get("datetime") if fecha else None,
            "link": enlace["href"].split("?")[0] if enlace else None,
        })
    return ofertas


def extraer_descripcion(link):
    # Entra a la pagina publica de la oferta y devuelve su descripcion completa.
    respuesta = requests.get(link, headers=HEADERS, timeout=20)
    respuesta.raise_for_status()
    soup = BeautifulSoup(respuesta.text, "html.parser")
    bloque = soup.select_one("div.show-more-less-html__markup")
    return bloque.get_text(" ", strip=True) if bloque else None


def extraer_ofertas():
    ofertas = []
    vistos = set()   # links ya guardados, para no repetir ofertas
    for rol in ROLES:
        for inicio in range(0, MAX_OFERTAS_POR_ROL, PASO):
            params = {"keywords": rol, "location": UBICACION, "start": inicio}
            try:
                respuesta = requests.get(URL, headers=HEADERS, params=params, timeout=20)
                respuesta.raise_for_status()
            except requests.RequestException as e:
                registrar_error(
                    FUENTE, "peticion_fallida",
                    f"Fallo el listado rol='{rol}' start={inicio}: {e}",
                    "se pasa al siguiente rol",
                )
                break

            # nos quedamos solo con las ofertas que no habiamos visto antes
            nuevas = [o for o in _parsear(respuesta.text, rol)
                      if o["link"] and o["link"] not in vistos]
            if not nuevas:        # sin ofertas nuevas = ya no hay mas para este rol
                break

            # entramos a cada oferta a traer su descripcion completa
            for oferta in nuevas:
                try:
                    oferta["descripcion"] = extraer_descripcion(oferta["link"])
                except requests.RequestException as e:
                    oferta["descripcion"] = None
                    registrar_error(
                        FUENTE, "peticion_fallida",
                        f"No se pudo abrir la oferta {oferta['link']}: {e}",
                        "descripcion=None, se continua con las demas",
                    )
                vistos.add(oferta["link"])
                time.sleep(1)     # pausa entre cada detalle (rate limiting)

            ofertas.extend(nuevas)
    return ofertas


def guardar_raw(ofertas):
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    # Nomenclatura Raw exigida: fuente_YYYY-MM-DD.json
    fecha = datetime.now().strftime("%Y-%m-%d")
    ruta = DIR_RAW / f"{FUENTE}_{fecha}.json"
    ruta.write_text(
        json.dumps(ofertas, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ruta


if __name__ == "__main__":
    ofertas = extraer_ofertas()
    destino = guardar_raw(ofertas)
    print(f"[{FUENTE}] {len(ofertas)} ofertas guardadas en {destino}")