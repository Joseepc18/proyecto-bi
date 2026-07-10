import sys
from pathlib import Path

# Permite importar las funciones de transformacion (viven en src/etl).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "etl"))

from transformacion import (
    _salario_computrabajo,
    _salario_internacional,
    _salario_mensual,
    _modalidad,
    _clasificar_rol,
    _detectar_tecnologias,
)


# ── salario local (Computrabajo) ──────────────────────────────────────────────

def test_salario_computrabajo_mensual_simple():
    assert _salario_computrabajo("482,00 US$ (Mensual)") == 482.0

def test_salario_computrabajo_ignora_comisiones():
    assert _salario_computrabajo("800,00 US$ (Mensual) + Comisiones") == 800.0

def test_salario_computrabajo_rango_punto_medio():
    # Un rango se resuelve al punto medio (mismo criterio que el internacional).
    assert _salario_computrabajo("1.200,00 - 1.500,00 US$ (Mensual)") == 1350.0


# ── salario internacional (Jooble / Remotive) ─────────────────────────────────

def test_salario_internacional_anual_a_mensual():
    # "$80k - $100k" anual -> punto medio 90k / 12 = 7500.
    assert _salario_internacional("$80k - $100k") == 7500.0

def test_salario_internacional_por_hora():
    # "$18 - $22/hr" -> 20/h * 160 h/mes = 3200.
    assert _salario_internacional("$18 - $22/hr") == 3200.0

def test_salario_internacional_ignora_texto_extra():
    # "No equity" no debe romper el parseo del rango en miles.
    assert _salario_internacional("$20k - $35k - No equity") == round(27500 / 12, 2)

def test_salario_mensual_fuente_sin_salario():
    # Fuentes que no publican salario devuelven None.
    assert _salario_mensual("cualquier cosa", "linkedin") is None


# ── modalidad ─────────────────────────────────────────────────────────────────

def test_modalidad_hibrido_desde_presencial_y_remoto():
    assert _modalidad("Presencial y remoto", "computrabajo") == "Hibrido"

def test_modalidad_jooble_es_no_especificado():
    # En Jooble "Full-time" es tipo de contrato, no modalidad.
    assert _modalidad("Full-time", "jooble") == "No especificado"


# ── clasificacion de rol ──────────────────────────────────────────────────────

def test_rol_qa_tiene_prioridad_sobre_desarrollador():
    # El orden de las reglas debe clasificar QA antes que Desarrollador.
    assert _clasificar_rol("QA Automation Developer")[0] == "QA Tester"

def test_rol_datos():
    assert _clasificar_rol("Científico de Datos Senior")[0] == "Analista-Cientifico de Datos"

def test_rol_desconocido_es_otro():
    assert _clasificar_rol("Community Manager") == ("Otro", "Otro")


# ── deteccion de tecnologias ──────────────────────────────────────────────────

def test_detecta_csharp_y_dotnet():
    tecs = _detectar_tecnologias("Experiencia en C# y .NET")
    assert "C#" in tecs and ".NET" in tecs

def test_no_falso_positivo_csharp():
    # "c#" no debe matchear dentro de otro token como "abc#1".
    assert _detectar_tecnologias("codigo abc#1 de prueba") == []
