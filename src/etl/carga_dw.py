import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parents[2]
PROCESSED = BASE / "data" / "processed"
STAGING = BASE / "data" / "staging"

# Conexion al DW: se lee del .env (la contrasena no va en el codigo).
load_dotenv()
CONEXION = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "proyecto_bi_dw"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "sslmode": os.getenv("DB_SSLMODE", "prefer"),  # 'require' para la nube (Neon)
}

MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Metadatos de cada fuente para dim_fuente.
FUENTES = {
    "computrabajo":  ("scraping", "local",          "https://ec.computrabajo.com"),
    "multitrabajos": ("scraping", "local",          "https://www.multitrabajos.com"),
    "buscojobs":     ("scraping", "local",          "https://www.buscojobs.com.ec"),
    "linkedin":      ("scraping", "local",          "https://www.linkedin.com/jobs"),
    "jooble":        ("api",      "internacional",  "https://jooble.org"),
    "remotive":      ("api",      "internacional",  "https://remotive.com"),
}

# Clasificacion del tipo de cada tecnologia (para dim_tecnologia).
TIPO_TECNOLOGIA = {
    "Python": "lenguaje", "Java": "lenguaje", "JavaScript": "lenguaje", "TypeScript": "lenguaje",
    "C#": "lenguaje", "C++": "lenguaje", "PHP": "lenguaje", "Ruby": "lenguaje", "Go": "lenguaje",
    "Kotlin": "lenguaje", "Swift": "lenguaje", "SQL": "lenguaje", "R": "lenguaje",
    "React": "framework", "Angular": "framework", "Vue": "framework", "Django": "framework",
    "Flask": "framework", "Spring": "framework", "Node.js": "framework", ".NET": "framework",
    "Laravel": "framework",
    "PostgreSQL": "base_datos", "MySQL": "base_datos", "MongoDB": "base_datos",
    "Oracle": "base_datos", "SQL Server": "base_datos",
    "AWS": "cloud", "Azure": "cloud", "GCP": "cloud",
    "Docker": "herramienta", "Kubernetes": "herramienta", "Git": "herramienta",
    "Power BI": "herramienta", "Tableau": "herramienta",
}


def _archivo_reciente(carpeta: Path, patron: str) -> Path:
    archivos = sorted(carpeta.glob(patron), reverse=True)
    if not archivos:
        raise FileNotFoundError(f"No hay archivos {patron} en {carpeta}")
    return archivos[0]


def _ubicacion_partes(ubicacion_raw, ambito):
    # "Guayaquil, Guayas" -> ciudad="Guayaquil", provincia="Guayas". Pais segun ambito.
    texto = str(ubicacion_raw).strip() if pd.notna(ubicacion_raw) else "No especificado"
    partes = [p.strip() for p in texto.split(",")]
    ciudad = partes[0] if partes and partes[0] else "No especificado"
    provincia = partes[1] if len(partes) > 1 else None
    pais = "Ecuador" if ambito == "local" else "Internacional"
    return ciudad, provincia, pais


# ── carga de dimensiones (devuelven un mapa valor -> id) ──────────────────────

def cargar_dim_fuente(cur):
    mapa = {}
    for nombre, (tipo, ambito, url) in FUENTES.items():
        cur.execute(
            "INSERT INTO dim_fuente (nombre_fuente, tipo_fuente, ambito, url) "
            "VALUES (%s,%s,%s,%s) RETURNING id_fuente",
            (nombre, tipo, ambito, url),
        )
        mapa[nombre] = cur.fetchone()[0]
    return mapa


def cargar_dim_modalidad(cur, df):
    mapa = {}
    for val in sorted(df["modalidad"].dropna().unique()):
        cur.execute(
            "INSERT INTO dim_modalidad (nombre_modalidad) VALUES (%s) RETURNING id_modalidad",
            (val,),
        )
        mapa[val] = cur.fetchone()[0]
    return mapa


def cargar_dim_rol(cur, df):
    mapa = {}
    roles = df[["nombre_rol", "categoria_rol"]].drop_duplicates()
    for _, r in roles.iterrows():
        cur.execute(
            "INSERT INTO dim_rol (nombre_rol, categoria_rol) VALUES (%s,%s) RETURNING id_rol",
            (r["nombre_rol"], r["categoria_rol"]),
        )
        mapa[r["nombre_rol"]] = cur.fetchone()[0]
    return mapa


def cargar_dim_ubicacion(cur, df):
    # Mapa keyed por (ciudad, provincia, pais) para no repetir ubicaciones.
    mapa = {}
    for _, r in df.iterrows():
        clave = _ubicacion_partes(r["ubicacion_raw"], r["ambito"])
        if clave not in mapa:
            cur.execute(
                "INSERT INTO dim_ubicacion (ciudad, provincia, pais) VALUES (%s,%s,%s) "
                "RETURNING id_ubicacion",
                clave,
            )
            mapa[clave] = cur.fetchone()[0]
    return mapa


def cargar_dim_tecnologia(cur, df):
    mapa = {}
    todas = set()
    for valor in df["tecnologias"].dropna():
        if valor:
            todas.update(valor.split("|"))
    for tec in sorted(todas):
        cur.execute(
            "INSERT INTO dim_tecnologia (nombre_tecnologia, tipo_tecnologia) "
            "VALUES (%s,%s) RETURNING id_tecnologia",
            (tec, TIPO_TECNOLOGIA.get(tec, "herramienta")),
        )
        mapa[tec] = cur.fetchone()[0]
    return mapa


def cargar_dim_tiempo(cur, df, salario_nac, sector):
    mapa = {}
    for fecha_str in sorted(df["fecha"].dropna().unique()):
        f = datetime.strptime(fecha_str, "%Y-%m-%d")
        cur.execute(
            "INSERT INTO dim_tiempo (fecha, dia, mes, nombre_mes, trimestre, semana, anio, "
            "salario_promedio_nacional, sector_referencia) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id_tiempo",
            (fecha_str, f.day, f.month, MESES[f.month], (f.month - 1) // 3 + 1,
             f.isocalendar()[1], f.year, salario_nac, sector),
        )
        mapa[fecha_str] = cur.fetchone()[0]
    return mapa


# ── carga de la tabla de hechos + puente ──────────────────────────────────────

def cargar_hechos(cur, df, m_fuente, m_modalidad, m_rol, m_ubic, m_tec, m_tiempo):
    n_hechos = 0
    n_puente = 0
    for _, r in df.iterrows():
        id_ubic = m_ubic[_ubicacion_partes(r["ubicacion_raw"], r["ambito"])]
        salario = None if pd.isna(r["salario_ofertado"]) else float(r["salario_ofertado"])

        cur.execute(
            "INSERT INTO fact_ofertas_empleo "
            "(id_tiempo, id_fuente, id_rol, id_ubicacion, id_modalidad, "
            " salario_ofertado, tiene_salario, es_remota, num_tecnologias, conteo_oferta) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id_oferta",
            (m_tiempo[r["fecha"]], m_fuente[r["fuente"]], m_rol[r["nombre_rol"]],
             id_ubic, m_modalidad[r["modalidad"]],
             salario, int(r["tiene_salario"]), int(r["es_remota"]),
             int(r["num_tecnologias"]), int(r["conteo_oferta"])),
        )
        id_oferta = cur.fetchone()[0]
        n_hechos += 1

        # tabla puente: una fila por tecnologia detectada en la oferta
        if pd.notna(r["tecnologias"]) and r["tecnologias"]:
            for tec in r["tecnologias"].split("|"):
                cur.execute(
                    "INSERT INTO puente_oferta_tecnologia (id_oferta, id_tecnologia) VALUES (%s,%s)",
                    (id_oferta, m_tec[tec]),
                )
                n_puente += 1
    return n_hechos, n_puente


def ejecutar_carga():
    if not CONEXION["password"]:
        raise RuntimeError("Falta DB_PASSWORD en el archivo .env")

    # 1. leer los datos limpios del E3
    ruta_ofertas = _archivo_reciente(PROCESSED, "validado_*.csv")
    df = pd.read_csv(ruta_ofertas)

    ruta_inec = _archivo_reciente(STAGING, "staging_inec_*.csv")
    inec = pd.read_csv(ruta_inec).iloc[0]
    salario_nac = float(inec["salario_promedio_nacional"])
    sector = str(inec["sector_referencia"])

    # 2. conectar y cargar
    conn = psycopg2.connect(**CONEXION)
    try:
        cur = conn.cursor()
        # Limpia las tablas antes de cargar para no duplicar si el script se corre
        # varias veces. RESTART IDENTITY reinicia los contadores de id; CASCADE
        # respeta el orden de las claves foraneas.
        cur.execute(
            "TRUNCATE puente_oferta_tecnologia, fact_ofertas_empleo, dim_tiempo, "
            "dim_modalidad, dim_fuente, dim_rol, dim_ubicacion, dim_tecnologia "
            "RESTART IDENTITY CASCADE;"
        )
        print("Cargando dimensiones...")
        m_fuente    = cargar_dim_fuente(cur)
        m_modalidad = cargar_dim_modalidad(cur, df)
        m_rol       = cargar_dim_rol(cur, df)
        m_ubic      = cargar_dim_ubicacion(cur, df)
        m_tec       = cargar_dim_tecnologia(cur, df)
        m_tiempo    = cargar_dim_tiempo(cur, df, salario_nac, sector)

        print("Cargando tabla de hechos y puente...")
        n_hechos, n_puente = cargar_hechos(
            cur, df, m_fuente, m_modalidad, m_rol, m_ubic, m_tec, m_tiempo
        )

        conn.commit()  # confirma todo si no hubo errores
    except Exception:
        conn.rollback()  # si algo falla, deshace todo (no deja datos a medias)
        raise
    finally:
        conn.close()

    print(f"\nCarga completada (origen: {ruta_ofertas.name})")
    print(f"  dim_fuente:     {len(m_fuente)}")
    print(f"  dim_modalidad:  {len(m_modalidad)}")
    print(f"  dim_rol:        {len(m_rol)}")
    print(f"  dim_ubicacion:  {len(m_ubic)}")
    print(f"  dim_tecnologia: {len(m_tec)}")
    print(f"  dim_tiempo:     {len(m_tiempo)}")
    print(f"  fact_ofertas_empleo:      {n_hechos}")
    print(f"  puente_oferta_tecnologia: {n_puente}")


if __name__ == "__main__":
    ejecutar_carga()
