import csv
from datetime import datetime
from pathlib import Path

# Log de errores del pipeline (control de calidad 3.6: registro de errores auditable).
# Una sola tabla append con timestamp + fuente + tipo + descripcion + accion tomada.
DIR_LOGS = Path(__file__).resolve().parents[1] / "data" / "logs"
ARCHIVO_LOG = DIR_LOGS / "registro_errores.csv"
COLUMNAS = ["timestamp", "fuente", "tipo_error", "descripcion", "accion_tomada"]


def registrar_error(fuente: str, tipo_error: str, descripcion: str, accion_tomada: str) -> None:
    DIR_LOGS.mkdir(parents=True, exist_ok=True)
    nuevo = not ARCHIVO_LOG.exists()
    with open(ARCHIVO_LOG, "a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        if nuevo:                       # cabecera solo la primera vez
            escritor.writerow(COLUMNAS)
        escritor.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            fuente, tipo_error, descripcion, accion_tomada,
        ])
