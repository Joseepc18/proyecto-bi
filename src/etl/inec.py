from datetime import datetime
from pathlib import Path

import pandas as pd

# Rutas portables: calculadas desde la ubicacion del archivo, no desde el CWD.
BASE = Path(__file__).resolve().parents[2]
# CUADRO N 50 - Salario promedio del empleo registrado, por rama de actividad (CIIU 4.1).
RUTA_INEC = (
    BASE / "data" / "raw" / "inec"
    / "Indicadores Laborales_Empleo_04_2026"
    / "4_2_1.csv"
)
STAGING = BASE / "data" / "staging"

# Codigo CIIU del sector que usamos como referencia nacional de TI.
SECTOR_CODIGO = "J"
SECTOR_NOMBRE = "Informacion y comunicacion"


def salario_sector_j() -> dict:
    # El CSV del INEC viene en latin-1 (no UTF-8); sin esto falla al leer las tildes.
    # Trae filas de titulo/encabezado; lo leemos sin cabecera y ubicamos a mano.
    df = pd.read_csv(RUTA_INEC, header=None, dtype=str, keep_default_na=False, encoding="latin-1")

    # Fila de meses: la unica que contiene "ene.-09" (primer mes de la serie).
    fila_meses = df[df.apply(lambda r: r.str.contains("ene.-09", regex=False).any(), axis=1)].iloc[0]
    # Ultima columna con mes = mes mas reciente de la serie (ej. abr.-26).
    ultima_col = max(i for i, v in fila_meses.items() if str(v).strip())
    periodo = str(fila_meses[ultima_col]).strip()

    # Fila del sector J (columna 1 = codigo CIIU).
    fila_sector = df[df[1].str.strip() == SECTOR_CODIGO].iloc[0]
    # Formato del numero: separador de miles con coma ("1,131" -> 1131).
    salario = float(str(fila_sector[ultima_col]).replace(",", ""))

    return {
        "periodo": periodo,
        "sector_codigo": SECTOR_CODIGO,
        "sector_referencia": SECTOR_NOMBRE,
        "salario_promedio_nacional": salario,
    }


def guardar_staging(dato: dict) -> Path:
    STAGING.mkdir(parents=True, exist_ok=True)
    hoy = datetime.today().strftime("%Y-%m-%d")
    salida = STAGING / f"staging_inec_{hoy}.csv"
    pd.DataFrame([dato]).to_csv(salida, index=False, encoding="utf-8")
    return salida


if __name__ == "__main__":
    dato = salario_sector_j()
    destino = guardar_staging(dato)
    print(f"[inec] Sector {dato['sector_codigo']} ({dato['sector_referencia']})")
    print(f"  Periodo:  {dato['periodo']}")
    print(f"  Salario nacional: ${dato['salario_promedio_nacional']:,.2f} /mes")
    print(f"  Guardado en: {destino}")
