import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

# Rutas portables: calculadas desde la ubicacion del archivo, no desde el CWD.
BASE      = Path(__file__).resolve().parents[2]
STAGING   = BASE / "data" / "staging"
PROCESSED = BASE / "data" / "processed"

# Para convertir salarios por hora a mensual: 40 h/semana x 4 semanas.
HORAS_MES = 160

# Diccionario de tecnologias: nombre normalizado -> textos a buscar en la descripcion.
# Tokens de 1-2 letras o palabras comunes (go, r, js) se evitan o se restringen
# a su forma inequivoca (golang, rstudio) para no inflar el conteo con falsos positivos.
TECNOLOGIAS = {
    "Python": ["python"],
    "Java": ["java"],
    "JavaScript": ["javascript"],
    "TypeScript": ["typescript"],
    "C#": ["c#", "csharp"],
    "C++": ["c++"],
    "PHP": ["php"],
    "Ruby": ["ruby"],
    "Go": ["golang"],
    "Kotlin": ["kotlin"],
    "Swift": ["swift"],
    "SQL": ["sql"],
    "R": ["rstudio", "r studio", "lenguaje r"],
    "React": ["react", "reactjs"],
    "Angular": ["angular"],
    "Vue": ["vue", "vuejs"],
    "Django": ["django"],
    "Flask": ["flask"],
    "Spring": ["spring", "spring boot"],
    "Node.js": ["node", "nodejs", "node.js"],
    ".NET": [".net", "dotnet"],
    "Laravel": ["laravel"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb", "mongo"],
    "Oracle": ["oracle"],
    "SQL Server": ["sql server", "sqlserver"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Git": ["git"],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
}

# Reglas para clasificar el rol a partir del titulo (orden importa: QA antes que dev).
REGLAS_ROL = [
    ("QA Tester", "Calidad",
     ["qa", "tester", "testing", "calidad", "quality", "automatizacion de pruebas"]),
    ("Analista-Cientifico de Datos", "Datos",
     ["cientifico de datos", "data scientist", "analista de datos", "data analyst",
      "ingeniero de datos", "data engineer", "business intelligence", "bi developer", "machine learning"]),
    ("Desarrollador de Software", "Desarrollo",
     ["desarrollador", "developer", "programador", "software engineer", "ingeniero de software",
      "desarrollo de software", "desarrollo web", "full stack", "full-stack", "backend",
      "back-end", "frontend", "front-end", "fullstack"]),
]


def _sin_acentos(texto: str) -> str:
    # Quita tildes para que las busquedas no fallen por "hibrido" vs "hibrido".
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _archivo_reciente() -> Path:
    # Excluimos staging_inec_*.csv: ese es la referencia del INEC, no las ofertas.
    archivos = sorted(
        (p for p in STAGING.glob("staging_*.csv") if "inec" not in p.name),
        reverse=True,
    )
    if not archivos:
        raise FileNotFoundError("No hay archivos staging_*.csv en data/staging/")
    return archivos[0]


# ── salario ───────────────────────────────────────────────────────────────────

def _salario_computrabajo(texto: str) -> float | None:
    # Formato espanol: "15.000,00 US$ (Mensual) + Comisiones" -> 15000.00 (ya mensual).
    # Si viene un rango ("1.200,00 - 1.500,00 US$") se toma el punto medio (igual que el internacional).
    cabeza = texto.split("US$")[0].strip()
    cabeza = cabeza.replace(".", "").replace(",", ".")  # . miles, , decimal
    numeros = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", cabeza)]
    return round(sum(numeros) / len(numeros), 2) if numeros else None


def _salario_internacional(texto: str) -> float | None:
    # Jooble y Remotive comparten formato: "$80k - $100k" (anual), "$34 per hour",
    # "$18 - $22/hr". La 'k' son miles (anual); "hour"/"/hr" indica por hora.
    # El sufijo 'k' se aplica por numero para no confundir "100 per hour" con miles.
    bajo = texto.lower()
    numeros = [
        float(val) * (1000 if k else 1)
        for val, k in re.findall(r"(\d+(?:\.\d+)?)\s*(k?)", bajo)
    ]
    if not numeros:
        return None
    valor = sum(numeros) / len(numeros)         # rango -> punto medio
    if "hour" in bajo or "/hr" in bajo or "hora" in bajo:
        valor *= HORAS_MES                      # por hora -> mensual
    elif "k" in bajo:
        valor /= 12                             # anual -> mensual
    return round(valor, 2)


def _salario_mensual(texto, fuente: str) -> float | None:
    if not isinstance(texto, str) or not texto.strip():
        return None
    if fuente == "computrabajo":
        return _salario_computrabajo(texto)
    if fuente in ("jooble", "remotive"):        # ambas APIs internacionales, mismo formato
        return _salario_internacional(texto)
    return None  # las demas fuentes no exponen salario


# ── modalidad ─────────────────────────────────────────────────────────────────

def _modalidad(texto, fuente: str) -> str:
    if not isinstance(texto, str) or not texto.strip():
        return "No especificado"
    t = _sin_acentos(texto.lower())
    # Jooble "Full-time" es tipo de contrato, no modalidad.
    if fuente == "jooble":
        return "No especificado"
    if "presencial" in t and "remoto" in t:    # Computrabajo "Presencial y remoto"
        return "Hibrido"
    if "hibrido" in t:
        return "Hibrido"
    if "remoto" in t or "remote" in t or "teletrabajo" in t:
        return "Remoto"
    if "presencial" in t:
        return "Presencial"
    return "No especificado"


# ── rol ───────────────────────────────────────────────────────────────────────

def _clasificar_rol(titulo) -> tuple[str, str]:
    if not isinstance(titulo, str):
        return "Otro", "Otro"
    t = _sin_acentos(titulo.lower())
    for nombre, categoria, claves in REGLAS_ROL:
        if any(_sin_acentos(c) in t for c in claves):
            return nombre, categoria
    return "Otro", "Otro"


# ── tecnologias ───────────────────────────────────────────────────────────────

def _detectar_tecnologias(descripcion) -> list[str]:
    if not isinstance(descripcion, str) or not descripcion.strip():
        return []
    texto = descripcion.lower()
    encontradas = []
    for nombre, patrones in TECNOLOGIAS.items():
        for p in patrones:
            # Limite por caracter alfanumerico (no \b) para que funcione con #, ++ y .
            # Ej: "c#" no debe matchear dentro de "abc#1"; ".net" matchea aunque tenga punto.
            if re.search(rf"(?<![a-z0-9]){re.escape(p)}(?![a-z0-9])", texto):
                encontradas.append(nombre)
                break
    return encontradas


# ── proceso principal ─────────────────────────────────────────────────────────

def transformar() -> tuple[pd.DataFrame, Path]:
    ruta = _archivo_reciente()
    df = pd.read_csv(ruta)

    df["salario_ofertado"] = df.apply(
        lambda r: _salario_mensual(r["salario_raw"], r["fuente"]), axis=1
    )
    df["tiene_salario"] = df["salario_ofertado"].notna().astype(int)

    df["modalidad"] = df.apply(
        lambda r: _modalidad(r["modalidad_raw"], r["fuente"]), axis=1
    )
    df["es_remota"] = (df["modalidad"] == "Remoto").astype(int)

    roles = df["titulo"].apply(_clasificar_rol)
    df["nombre_rol"]   = roles.apply(lambda x: x[0])
    df["categoria_rol"] = roles.apply(lambda x: x[1])

    tecnologias = df["descripcion"].apply(_detectar_tecnologias)
    df["tecnologias"]     = tecnologias.apply(lambda lst: "|".join(lst))
    df["num_tecnologias"] = tecnologias.apply(len)

    df["conteo_oferta"] = 1
    return df, ruta


def ejecutar_transformacion():
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df, origen = transformar()

    hoy = datetime.today().strftime("%Y-%m-%d")
    salida = PROCESSED / f"transformacion_{hoy}.csv"
    df.to_csv(salida, index=False, encoding="utf-8")

    print(f"Transformacion completada: {len(df)} ofertas -> {salida}")
    print(f"  (origen: {origen.name})\n")
    print("Ofertas con salario mensual:")
    print(f"  Con salario: {df['tiene_salario'].sum()}")
    if df["tiene_salario"].sum():
        con = df[df["tiene_salario"] == 1]["salario_ofertado"]
        print(f"  Rango: ${con.min():,.0f} - ${con.max():,.0f}  (prom: ${con.mean():,.0f})")
    print("\nModalidad:")
    print(df["modalidad"].value_counts().to_string())
    print("\nRol:")
    print(df["nombre_rol"].value_counts().to_string())
    print("\nTop tecnologias detectadas:")
    top = df["tecnologias"].str.split("|").explode()
    top = top[top != ""].value_counts().head(10)
    print(top.to_string())


if __name__ == "__main__":
    ejecutar_transformacion()
