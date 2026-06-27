import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Rutas portables y acceso a utils_log (validacion vive en src/etl).
BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils_log import registrar_error

PROCESSED = BASE / "data" / "processed"

# Rango mensual valido para una oferta de TI en USD (decision del equipo).
# Fuera de este rango el salario se considera error de captura.
SALARIO_MIN = 400
SALARIO_MAX = 10000

# Campos minimos que toda oferta debe traer para ser util en el DW.
CAMPOS_CLAVE = ["titulo", "fuente", "fecha_carga"]
# Campos que deberian venir poblados (salario se excluye: su ausencia es estructural).
CAMPOS_COMPLETITUD = ["titulo", "ubicacion_raw", "fecha", "descripcion"]


def _archivo_reciente() -> Path:
    archivos = sorted(PROCESSED.glob("transformacion_*.csv"), reverse=True)
    if not archivos:
        raise FileNotFoundError("No hay transformacion_*.csv en data/processed/")
    return archivos[0]


def _es_fecha_valida(valor) -> bool:
    # Formato esperado tras el staging: AAAA-MM-DD.
    return isinstance(valor, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor))


# ── 3.1 a 3.6: controles de calidad sobre el dataframe ────────────────────────

def validar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    reporte = {"filas_inicio": len(df)}

    # 3.2 NULOS CRITICOS — titulo: sin titulo no se puede clasificar la oferta -> eliminar.
    sin_titulo = int(df["titulo"].isna().sum())
    if sin_titulo:
        registrar_error("validacion", "nulo_critico",
                        f"{sin_titulo} registros sin titulo", "registros eliminados")
    df = df[df["titulo"].notna()].copy()
    reporte["descartadas_sin_titulo"] = sin_titulo

    # 3.1 DUPLICADOS — criterio de unicidad: mismo 'link' (clave natural de la oferta).
    #     Si no hay link, se usa (fuente|titulo|empresa). Estrategia: conservar el mas
    #     completo (la fila con mas campos no nulos). Ojo: la misma vacante en dos
    #     portales NO es duplicado (clave distinta), se conserva (lo exige el KPI 4).
    df["_clave"] = df["link"].fillna(
        df["fuente"].astype(str) + "|" + df["titulo"].astype(str) + "|" + df["empresa"].astype(str)
    )
    df["_completitud"] = df.notna().sum(axis=1)
    df = df.sort_values("_completitud", ascending=False)
    antes = len(df)
    df = df.drop_duplicates(subset="_clave", keep="first")
    n_dup = antes - len(df)
    df = df.drop(columns=["_clave", "_completitud"]).sort_index()
    if n_dup:
        registrar_error("validacion", "duplicado",
                        f"{n_dup} ofertas duplicadas (misma clave de unicidad)",
                        "eliminadas, se conserva la fila mas completa")
    reporte["duplicados_eliminados"] = n_dup

    # 3.2 NULOS NO CRITICOS — matriz de resolucion (imputar / valor por defecto):
    #   fecha: si falta -> imputar con la fecha de carga (mantiene consistencia temporal).
    fecha_imputada = int(df["fecha"].isna().sum())
    df.loc[df["fecha"].isna(), "fecha"] = df.loc[df["fecha"].isna(), "fecha_carga"]
    reporte["fechas_imputadas"] = fecha_imputada
    #   ubicacion: si falta -> "No especificado" (no se puede inferir con fiabilidad).
    ubic_default = int(df["ubicacion_raw"].isna().sum())
    df.loc[df["ubicacion_raw"].isna(), "ubicacion_raw"] = "No especificado"
    reporte["ubicaciones_default"] = ubic_default
    #   salario: NO se imputa. Su ausencia es estructural (la fuente no lo publica);
    #            imputarlo falsearia el KPI de salario. Se conserva NULL.

    # 3.3 / 3.7 RANGO DE SALARIO: fuera de [400, 10000] = error de captura.
    #     Se anula solo el salario (NULL) y se conserva la oferta para los demas KPIs.
    fuera = df["salario_ofertado"].notna() & (
        (df["salario_ofertado"] < SALARIO_MIN) | (df["salario_ofertado"] > SALARIO_MAX)
    )
    n_fuera = int(fuera.sum())
    if n_fuera:
        registrar_error("validacion", "salario_fuera_de_rango",
                        f"{n_fuera} salarios fuera de [{SALARIO_MIN}, {SALARIO_MAX}] USD/mes",
                        "salario anulado (NULL), se conserva la oferta")
    df.loc[fuera, "salario_ofertado"] = pd.NA
    df.loc[fuera, "tiene_salario"] = 0
    reporte["salarios_anulados"] = n_fuera

    # 3.3 FORMATO DE FECHA: cuantas fechas no quedaron en AAAA-MM-DD.
    fechas_malas = (~df["fecha"].apply(_es_fecha_valida)) & df["fecha"].notna()
    reporte["fechas_formato_invalido"] = int(fechas_malas.sum())

    # 3.6 TRAZABILIDAD: toda fila debe conservar fuente + fecha_carga.
    reporte["sin_trazabilidad"] = int(df[CAMPOS_CLAVE].isna().any(axis=1).sum())

    reporte["filas_final"] = len(df)
    return df, reporte


def _completitud_por_fuente(df: pd.DataFrame) -> pd.DataFrame:
    # % de no nulos por campo relevante, agrupado por fuente (metrica de calidad).
    campos = ["titulo", "ubicacion_raw", "fecha", "salario_ofertado", "descripcion"]
    filas = []
    for fuente, grupo in df.groupby("fuente"):
        fila = {"fuente": fuente, "ofertas": len(grupo)}
        for c in campos:
            fila[c] = f"{grupo[c].notna().mean() * 100:.0f}%"
        filas.append(fila)
    return pd.DataFrame(filas)


# ── 3.7 Reporte final de metricas de calidad ──────────────────────────────────

def _tasa_completitud_general(df: pd.DataFrame) -> float:
    # Promedio de no nulos sobre los campos que deberian venir poblados.
    return df[CAMPOS_COMPLETITUD].notna().mean().mean() * 100


def guardar_reporte(df: pd.DataFrame, reporte: dict, hoy: str) -> Path:
    completitud = _tasa_completitud_general(df)
    incidencias = (
        reporte["descartadas_sin_titulo"]
        + reporte["duplicados_eliminados"]
        + reporte["salarios_anulados"]
    )
    tasa_error = incidencias / reporte["filas_inicio"] * 100 if reporte["filas_inicio"] else 0

    lineas = [
        f"# Reporte Final de Metricas de Calidad — {hoy}",
        "",
        "## Consolidado del pipeline",
        "",
        "| Metrica Operacional | Valor |",
        "|---|---|",
        f"| Total registros crudos procesados (Raw) | {reporte['filas_inicio']} |",
        f"| Total registros consolidados aptos (Staging) | {reporte['filas_final']} |",
        f"| Tasa de completitud general | {completitud:.1f}% |",
        f"| Registros depurados por duplicados | {reporte['duplicados_eliminados']} |",
        f"| Registros eliminados por nulos criticos | {reporte['descartadas_sin_titulo']} |",
        f"| Fechas imputadas (con fecha de carga) | {reporte['fechas_imputadas']} |",
        f"| Ubicaciones puestas a 'No especificado' | {reporte['ubicaciones_default']} |",
        f"| Salarios anulados por rango invalido | {reporte['salarios_anulados']} |",
        f"| Tasa de incidencias de calidad | {tasa_error:.1f}% |",
        "",
        "## Completitud por fuente (% no nulos)",
        "",
    ]
    tabla = _completitud_por_fuente(df)
    lineas.append("| " + " | ".join(tabla.columns) + " |")
    lineas.append("|" + "---|" * len(tabla.columns))
    for _, r in tabla.iterrows():
        lineas.append("| " + " | ".join(str(v) for v in r.values) + " |")

    salida = PROCESSED / f"reporte_calidad_{hoy}.md"
    salida.write_text("\n".join(lineas), encoding="utf-8")
    return salida


def ejecutar_validacion():
    ruta = _archivo_reciente()
    df = pd.read_csv(ruta)
    df_val, reporte = validar(df)

    hoy = datetime.today().strftime("%Y-%m-%d")
    salida = PROCESSED / f"validado_{hoy}.csv"
    df_val.to_csv(salida, index=False, encoding="utf-8")
    reporte_md = guardar_reporte(df_val, reporte, hoy)

    print(f"Validacion completada -> {salida}")
    print(f"  (origen: {ruta.name})\n")
    print("Controles de calidad:")
    print(f"  Filas iniciales:            {reporte['filas_inicio']}")
    print(f"  Descartadas sin titulo:     {reporte['descartadas_sin_titulo']}")
    print(f"  Duplicados eliminados:      {reporte['duplicados_eliminados']}")
    print(f"  Fechas imputadas:           {reporte['fechas_imputadas']}")
    print(f"  Ubicaciones por defecto:    {reporte['ubicaciones_default']}")
    print(f"  Salarios anulados (rango):  {reporte['salarios_anulados']}")
    print(f"  Fechas formato invalido:    {reporte['fechas_formato_invalido']}")
    print(f"  Filas sin trazabilidad:     {reporte['sin_trazabilidad']}")
    print(f"  Filas finales:              {reporte['filas_final']}")
    print(f"\nCompletitud general: {_tasa_completitud_general(df_val):.1f}%")
    print("\nCompletitud por fuente (% no nulos):")
    print(_completitud_por_fuente(df_val).to_string(index=False))
    print(f"\nReporte consolidado -> {reporte_md}")


if __name__ == "__main__":
    ejecutar_validacion()
