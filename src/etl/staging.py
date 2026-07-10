import json
import pandas as pd
import re
from datetime import datetime, timedelta
from pathlib import Path

# ── rutas base ───────────────────────────────────────────────────────────────
# Rutas calculadas desde la ubicacion del archivo (portables: corren desde cualquier carpeta).
BASE    = Path(__file__).resolve().parents[2]
RAW     = BASE / "data" / "raw"
STAGING = BASE / "data" / "staging"

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# ── helpers generales ─────────────────────────────────────────────────────────

def _texto(valor) -> str | None:
    if not valor:
        return None
    return str(valor).strip() or None

def _archivo_reciente(carpeta: Path) -> Path | None:
    archivos = sorted(carpeta.glob("*.json"), reverse=True)
    return archivos[0] if archivos else None

def _fecha_de_nombre(ruta: Path) -> datetime:
    # El nombre trae la fecha: fuente_YYYY-MM-DD.json (o formatos antiguos DD-MM-YYYY).
    nombre = ruta.stem
    m = re.search(r"(\d{4}-\d{2}-\d{2})", nombre)        # YYYY-MM-DD en cualquier parte
    if m:
        return datetime.strptime(m.group(1), "%Y-%m-%d")
    m = re.search(r"(\d{2}-\d{2}-\d{4})", nombre)        # DD-MM-YYYY (compatibilidad)
    if m:
        return datetime.strptime(m.group(1), "%d-%m-%Y")
    return datetime.today()

def _normalizar_fecha(fecha_raw: str | None, fecha_carga: datetime) -> str | None:
    if not fecha_raw:
        return None
    s = str(fecha_raw).strip().lower()

    # "hoy"
    if s in ("hoy", "today"):
        return fecha_carga.strftime("%Y-%m-%d")

    # "hace N días" / "hace 1 día"
    m = re.match(r"hace\s+(\d+)\s+d[ií]a", s)
    if m:
        return (fecha_carga - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

    # "2 de junio"
    m = re.match(r"(\d{1,2})\s+de\s+(\w+)", s)
    if m:
        mes = MESES.get(m.group(2))
        if mes:
            return f"{fecha_carga.year}-{mes:02d}-{int(m.group(1)):02d}"

    # ISO con T: "2026-06-12T22:04:24.281Z"
    m = re.match(r"(\d{4}-\d{2}-\d{2})t", s)
    if m:
        return m.group(1)

    # DD-MM-YYYY
    m = re.match(r"(\d{2})-(\d{2})-(\d{4})$", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

    # YYYY-MM-DD ya normalizado
    m = re.match(r"(\d{4}-\d{2}-\d{2})$", s)
    if m:
        return m.group(1)

    return None

def _fila(titulo, empresa, ubicacion, salario_raw, modalidad_raw,
          fecha_raw, descripcion, link, fuente, ambito, fecha_carga: datetime) -> dict:
    # Una oferta no puede publicarse despues de la fecha de extraccion; si la fecha
    # normalizada cae en el futuro, es un parseo dudoso -> se deja nula (luego se imputa).
    fecha = _normalizar_fecha(fecha_raw, fecha_carga)
    if fecha and fecha > fecha_carga.strftime("%Y-%m-%d"):
        fecha = None
    return {
        "titulo":        _texto(titulo),
        "empresa":       _texto(empresa),
        "ubicacion_raw": _texto(ubicacion),
        "salario_raw":   _texto(salario_raw),
        "modalidad_raw": _texto(modalidad_raw),
        "fecha_raw":     _texto(fecha_raw),
        "fecha":         fecha,
        "descripcion":   _texto(descripcion),
        "link":          _texto(link),
        "fuente":        fuente,
        "ambito":        ambito,
        "fecha_carga":   fecha_carga.strftime("%Y-%m-%d"),
    }

# ── lectores por fuente ───────────────────────────────────────────────────────

def _leer_computrabajo(ruta: Path, fecha_carga: datetime) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    return [
        _fila(
            titulo=o.get("titulo"),
            empresa=o.get("empresa"),
            ubicacion=o.get("ubicacion"),
            salario_raw=o.get("salario"),
            modalidad_raw=o.get("modalidad"),
            fecha_raw=o.get("fecha"),
            descripcion=o.get("descripcion"),
            link=o.get("link"),
            fuente="computrabajo",
            ambito="local",
            fecha_carga=fecha_carga,
        )
        for o in datos
    ]

def _leer_multitrabajos(ruta: Path, fecha_carga: datetime) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    return [
        _fila(
            titulo=o.get("titulo"),
            empresa=o.get("empresa"),
            ubicacion=o.get("ubicacion"),
            salario_raw=o.get("salario"),
            modalidad_raw=o.get("modalidad"),
            fecha_raw=o.get("fecha"),
            descripcion=o.get("descripcion"),
            link=o.get("link"),
            fuente="multitrabajos",
            ambito="local",
            fecha_carga=fecha_carga,
        )
        for o in datos
    ]

def _leer_buscojobs(ruta: Path, fecha_carga: datetime) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    return [
        _fila(
            titulo=o.get("titulo"),
            empresa=o.get("empresa"),
            ubicacion=o.get("ubicacion"),
            salario_raw=o.get("salario"),
            modalidad_raw=o.get("modalidad"),
            fecha_raw=o.get("fecha"),
            descripcion=o.get("descripcion"),
            link=o.get("link"),
            fuente="buscojobs",
            ambito="local",
            fecha_carga=fecha_carga,
        )
        for o in datos
    ]

def _leer_linkedin(ruta: Path, fecha_carga: datetime) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    return [
        _fila(
            titulo=o.get("titulo"),
            empresa=o.get("empresa"),
            ubicacion=o.get("ubicacion"),
            salario_raw=o.get("salario"),
            modalidad_raw=None,  # LinkedIn guest no expone modalidad
            fecha_raw=o.get("fecha"),
            descripcion=o.get("descripcion"),
            link=o.get("link"),
            fuente="linkedin",
            ambito="local",
            fecha_carga=fecha_carga,
        )
        for o in datos
    ]

def _leer_jooble(ruta: Path, fecha_carga: datetime) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    lista = datos if isinstance(datos, list) else datos.get("jobs", [])
    return [
        _fila(
            titulo=o.get("title"),
            empresa=o.get("company"),
            ubicacion=o.get("location"),
            salario_raw=o.get("salary"),
            modalidad_raw=o.get("type"),
            fecha_raw=o.get("updated"),
            descripcion=o.get("snippet"),
            link=o.get("link"),
            fuente="jooble",
            ambito="internacional",
            fecha_carga=fecha_carga,
        )
        for o in lista
    ]

def _leer_remotive(ruta: Path, fecha_carga: datetime) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    lista = datos if isinstance(datos, list) else datos.get("jobs", [])
    return [
        _fila(
            titulo=o.get("title"),
            empresa=o.get("company_name"),
            ubicacion=o.get("candidate_required_location"),
            salario_raw=o.get("salary"),
            modalidad_raw="Remoto",  # Remotive es 100% trabajo remoto
            fecha_raw=o.get("publication_date"),
            descripcion=o.get("description"),
            link=o.get("url"),
            fuente="remotive",
            ambito="internacional",
            fecha_carga=fecha_carga,
        )
        for o in lista
    ]

# ── función principal ─────────────────────────────────────────────────────────

LECTORES = {
    "computrabajo": _leer_computrabajo,
    "multitrabajos": _leer_multitrabajos,
    "buscojobs":    _leer_buscojobs,
    "linkedin":     _leer_linkedin,
    "jooble":       _leer_jooble,
    "remotive":     _leer_remotive,
}

def ejecutar_staging():
    STAGING.mkdir(parents=True, exist_ok=True)
    todos = []

    for fuente, lector in LECTORES.items():
        carpeta = RAW / fuente
        ruta = _archivo_reciente(carpeta)
        if ruta is None:
            print(f"[ADVERTENCIA] No hay archivos en {carpeta}, se omite.")
            continue
        fecha_carga = _fecha_de_nombre(ruta)
        filas = lector(ruta, fecha_carga)
        todos.extend(filas)
        print(f"[OK] {fuente}: {len(filas)} ofertas leídas desde {ruta.name}")

    df = pd.DataFrame(todos)

    hoy = datetime.today().strftime("%Y-%m-%d")
    salida = STAGING / f"staging_{hoy}.csv"
    df.to_csv(salida, index=False, encoding="utf-8")

    print(f"\nStaging completado: {len(df)} ofertas en total -> {salida}")
    print("\nOfertas por fuente:")
    print(df.groupby("fuente")["titulo"].count().to_string())
    print("\nOfertas con fecha normalizada:")
    print(f"  Con fecha: {df['fecha'].notna().sum()}")
    print(f"  Sin fecha: {df['fecha'].isna().sum()}")
    print("\nOfertas con salario:")
    print(f"  Con salario: {df['salario_raw'].notna().sum()}")
    print(f"  Sin salario: {df['salario_raw'].isna().sum()}")

if __name__ == "__main__":
    ejecutar_staging()
