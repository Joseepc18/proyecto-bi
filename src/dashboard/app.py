import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from dotenv import load_dotenv

# Conexion al DW (se lee del .env, igual que carga_dw.py).
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
CONEXION = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "proyecto_bi_dw"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}

st.set_page_config(page_title="BI - Mercado Laboral Tech Ecuador",
                   page_icon="📊", layout="wide")

# Paleta navy + naranja (estilo dashboard administrativo).
PALETA = ["#1B3A5B", "#F5A623", "#4A90D9", "#2DC8A8", "#9B59B6", "#E26D5C"]

st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 2rem; max-width: 1300px;}
/* Sidebar navy */
[data-testid="stSidebar"] {background: linear-gradient(180deg, #1B3A5B 0%, #14293f 100%);}
[data-testid="stSidebar"] * {color: #E8EEF5 !important;}
[data-testid="stSidebar"] [role="radiogroup"] label {padding: 9px 12px; border-radius: 10px;
    margin-bottom: 3px; transition: .15s;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background: rgba(255,255,255,0.08);}
.brand {text-align:center; padding: 8px 0 18px 0; border-bottom:1px solid rgba(255,255,255,.12);
    margin-bottom: 16px;}
.brand-logo {font-size: 2.6rem;}
.brand-name {font-weight: 800; font-size: 1.15rem; margin-top: 4px;}
.brand-sub {font-size: .78rem; opacity:.7;}
/* Tarjetas de metricas */
.mcard {background:#fff; border-radius:16px; padding:18px 20px;
    box-shadow:0 4px 16px rgba(27,42,65,.08); height:108px;}
.mcard.dark {background: linear-gradient(135deg, #1B3A5B 0%, #265080 100%);}
.mcard.dark .mcard-label {color:#C5D4E6;}
.mcard.dark .mcard-val {color:#fff;}
.mcard-top {display:flex; justify-content:space-between; align-items:center;}
.mcard-label {color:#7A8AA0; font-size:.78rem; font-weight:700; text-transform:uppercase;
    letter-spacing:.4px;}
.mcard-ic {font-size:1.4rem;}
.mcard-val {font-size:1.9rem; font-weight:800; color:#1B3A5B; margin-top:10px;}
/* Tarjetas de graficos (contenedores con borde) */
[data-testid="stVerticalBlockBorderWrapper"] {background:#fff; border:none !important;
    border-radius:16px; box-shadow:0 4px 16px rgba(27,42,65,.06); padding:8px 10px;}
h1, h2, h3, h4 {color:#1B2A41;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=600)
def consultar(sql: str) -> pd.DataFrame:
    conn = psycopg2.connect(**CONEXION)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        columnas = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columnas)
    finally:
        conn.close()


def estilo(fig, alto=340, leyenda=False):
    # leyenda=True en los graficos de varias series (para saber que es cada color).
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", colorway=PALETA,
                      font=dict(family="Segoe UI, sans-serif", color="#43506b", size=13),
                      margin=dict(l=10, r=10, t=48 if leyenda else 24, b=10),
                      height=alto, showlegend=leyenda,
                      legend=dict(orientation="h", y=1.12, x=0, title=""))
    fig.update_xaxes(gridcolor="rgba(27,42,65,0.06)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(27,42,65,0.06)", zeroline=False)
    return fig


def metrica(col, label, valor, icono, dark=False):
    clase = "mcard dark" if dark else "mcard"
    col.markdown(
        f'<div class="{clase}"><div class="mcard-top">'
        f'<span class="mcard-label">{label}</span><span class="mcard-ic">{icono}</span></div>'
        f'<div class="mcard-val">{valor}</div></div>', unsafe_allow_html=True)


# ── Sidebar: marca + navegacion ───────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-logo">📊</div>'
                '<div class="brand-name">BI Mercado Tech</div>'
                '<div class="brand-sub">Ecuador · Entregable 5</div></div>',
                unsafe_allow_html=True)
    seccion = st.radio("Navegación",
                       ["📈 Resumen", "💰 Salarios", "🛠️ Tecnologías", "🌎 Modalidad"],
                       label_visibility="collapsed")

# ── Datos para las metricas ───────────────────────────────────────────────────
total = consultar("SELECT COUNT(*) AS n FROM fact_ofertas_empleo").iloc[0]["n"]
# KPI 6: solo salario LOCAL vs nacional del INEC (Ecuador vs Ecuador, ver consultas_kpis.sql).
kpi6 = consultar("""
    SELECT ROUND(AVG(f.salario_ofertado)/MAX(t.salario_promedio_nacional),2) AS relacion,
           MAX(t.salario_promedio_nacional) AS nacional
    FROM fact_ofertas_empleo f
    JOIN dim_tiempo t  ON f.id_tiempo = t.id_tiempo
    JOIN dim_fuente fu ON f.id_fuente = fu.id_fuente
    WHERE f.tiene_salario = 1 AND fu.ambito = 'local'
""").iloc[0]
kpi2 = consultar("SELECT ROUND(100.0*SUM(es_remota)/COUNT(*),1) AS tasa "
                 "FROM fact_ofertas_empleo").iloc[0]["tasa"]
sal_local = consultar("""
    SELECT ROUND(AVG(f.salario_ofertado),0) AS s FROM fact_ofertas_empleo f
    JOIN dim_fuente fu ON f.id_fuente = fu.id_fuente
    WHERE f.tiene_salario = 1 AND fu.ambito = 'local'
""").iloc[0]["s"]
# Transparencia salarial: % de ofertas que publican salario (calculado en vivo, no fijo).
sal_pub = consultar("""
    SELECT SUM(tiene_salario) AS con, COUNT(*) AS tot,
           ROUND(100.0*SUM(tiene_salario)/COUNT(*),1) AS pct
    FROM fact_ofertas_empleo
""").iloc[0]

# ── Encabezado + tarjetas de metricas ─────────────────────────────────────────
st.markdown("### Mercado Laboral Tech en Ecuador")
st.caption("Plataforma de Inteligencia de Negocios · Análisis comparativo de datos heterogéneos")
st.write("")

m1, m2, m3, m4 = st.columns(4)
metrica(m1, "Total de ofertas", f"{int(total)}", "📋", dark=True)
metrica(m2, "Salario medio local", f"${float(sal_local):,.0f}", "💵")
metrica(m3, "Tasa remota", f"{float(kpi2)}%", "🏠")
metrica(m4, "TI local vs. nacional", f"{float(kpi6['relacion'])}x", "⭐")
st.write("")


# ── Helpers de consultas de cada grafico ──────────────────────────────────────
def g_salario_rol():
    # KPI 1 - salario promedio por rol (AVG), solo ofertas locales con salario.
    df = consultar("""
        SELECT r.nombre_rol,
               ROUND(AVG(f.salario_ofertado), 0) AS prom,
               COUNT(*) AS n
        FROM fact_ofertas_empleo f
        JOIN dim_rol r ON f.id_rol = r.id_rol
        JOIN dim_fuente fu ON f.id_fuente = fu.id_fuente
        WHERE f.tiene_salario = 1 AND fu.ambito = 'local'
        GROUP BY r.nombre_rol ORDER BY prom DESC
    """)
    df["prom"] = df["prom"].astype(float)
    df["nombre_rol"] = df["nombre_rol"].replace("Otro", "Otros roles de TI")
    df["etq"] = df["nombre_rol"] + " (n=" + df["n"].astype(str) + ")"
    fig = px.bar(df, x="etq", y="prom", text_auto=".0f", color="nombre_rol",
                 labels={"etq": "", "prom": "Salario promedio (USD)"})
    return estilo(fig)


def g_tecnologias(alto=340):
    # KPI 3 - indice de demanda: (menciones / total de ofertas) * 100, segun el E1.
    df = consultar("""
        SELECT t.nombre_tecnologia,
               ROUND(100.0*COUNT(*) / (SELECT COUNT(*) FROM fact_ofertas_empleo), 1) AS pct
        FROM puente_oferta_tecnologia p
        JOIN dim_tecnologia t ON p.id_tecnologia = t.id_tecnologia
        GROUP BY t.nombre_tecnologia ORDER BY pct DESC LIMIT 10
    """)
    df["pct"] = df["pct"].astype(float)
    fig = px.bar(df.sort_values("pct"), x="pct", y="nombre_tecnologia",
                 orientation="h", text_auto=".1f",
                 labels={"pct": "% de ofertas que la mencionan", "nombre_tecnologia": ""})
    fig.update_traces(marker_color="#1B3A5B")
    return estilo(fig, alto)


def g_modalidad():
    df = consultar("""
        SELECT m.nombre_modalidad, COUNT(*) AS ofertas
        FROM fact_ofertas_empleo f JOIN dim_modalidad m ON f.id_modalidad = m.id_modalidad
        GROUP BY m.nombre_modalidad ORDER BY ofertas DESC
    """)
    fig = px.pie(df, names="nombre_modalidad", values="ofertas", hole=0.55)
    fig.update_traces(textposition="outside", textinfo="percent+label")
    return estilo(fig)


# ── Contenido segun la seccion elegida ────────────────────────────────────────
if seccion == "📈 Resumen":
    col1, col2 = st.columns([1.3, 1])
    with col1.container(border=True):
        st.markdown("##### 💰 Salario promedio por rol (Ecuador)")
        st.plotly_chart(g_salario_rol(), use_container_width=True)
    with col2.container(border=True):
        st.markdown("##### 🏠 Modalidad de trabajo")
        st.plotly_chart(g_modalidad(), use_container_width=True)
    with st.container(border=True):
        st.markdown("##### 🛠️ Tecnologías más demandadas")
        st.plotly_chart(g_tecnologias(380), use_container_width=True)
    st.success(
        f"🔎 **Insight principal:** solo el **{float(sal_pub['pct'])}%** de las ofertas "
        f"({int(sal_pub['con'])} de {int(sal_pub['tot'])}) publica el salario. Entre las locales "
        f"que sí lo hacen, el promedio (${float(sal_local):,.0f}) equivale a "
        f"**{float(kpi6['relacion'])}×** el salario nacional del INEC "
        f"(${float(kpi6['nacional']):,.0f}) del sector información y comunicación.")

elif seccion == "💰 Salarios":
    st.warning(f"🔍 **Hallazgo — opacidad salarial:** solo el **{float(sal_pub['pct'])}%** de las "
               f"ofertas ({int(sal_pub['con'])} de {int(sal_pub['tot'])}) publica el salario; el "
               "resto lo declara \"a convenir\". Por eso los análisis salariales se basan en "
               "muestras reducidas y se interpretan como indicativos.")
    col1, col2 = st.columns(2)
    with col1.container(border=True):
        st.markdown("##### 💰 Salario promedio por rol (Ecuador)")
        st.plotly_chart(g_salario_rol(), use_container_width=True)
    with col2.container(border=True):
        st.markdown("##### 🌎 Salario local vs. internacional")
        df = consultar("""
            SELECT fu.ambito,
                   ROUND(AVG(f.salario_ofertado), 0) AS prom,
                   COUNT(*) AS n
            FROM fact_ofertas_empleo f JOIN dim_fuente fu ON f.id_fuente = fu.id_fuente
            WHERE f.tiene_salario = 1 GROUP BY fu.ambito
        """)
        df["prom"] = df["prom"].astype(float)
        df["etq"] = df["ambito"] + " (n=" + df["n"].astype(str) + ")"
        fig = px.bar(df, x="etq", y="prom", text_auto=".0f", color="ambito",
                     labels={"etq": "", "prom": "Salario promedio (USD)"})
        st.plotly_chart(estilo(fig), use_container_width=True)
    with st.container(border=True):
        st.markdown("##### 📋 Completitud de los datos")
        df = consultar("""
            SELECT 'Ubicación' AS campo,
                   ROUND(100.0*SUM(CASE WHEN u.ciudad <> 'No especificado' THEN 1 ELSE 0 END)/COUNT(*),1) AS pct
            FROM fact_ofertas_empleo f JOIN dim_ubicacion u ON f.id_ubicacion = u.id_ubicacion
            UNION ALL SELECT 'Modalidad',
                   ROUND(100.0*SUM(CASE WHEN m.nombre_modalidad <> 'No especificado' THEN 1 ELSE 0 END)/COUNT(*),1)
            FROM fact_ofertas_empleo f JOIN dim_modalidad m ON f.id_modalidad = m.id_modalidad
            UNION ALL SELECT 'Tecnologías', ROUND(100.0*SUM(CASE WHEN num_tecnologias>0 THEN 1 ELSE 0 END)/COUNT(*),1)
            FROM fact_ofertas_empleo
            UNION ALL SELECT 'Salario', ROUND(100.0*SUM(tiene_salario)/COUNT(*),1) FROM fact_ofertas_empleo
        """)
        df["pct"] = df["pct"].astype(float)
        fig = px.bar(df.sort_values("pct"), x="pct", y="campo", orientation="h",
                     text_auto=".1f", range_x=[0, 100], labels={"pct": "% lleno", "campo": ""})
        fig.update_traces(marker_color="#F5A623")
        st.plotly_chart(estilo(fig, 260), use_container_width=True)

elif seccion == "🛠️ Tecnologías":
    with st.container(border=True):
        st.markdown("##### 🛠️ Tecnologías más demandadas (top 10)")
        st.plotly_chart(g_tecnologias(440), use_container_width=True)
    st.info("**SQL** y **Python** lideran la demanda, lo que refleja un mercado orientado a la "
            "gestión y el análisis de datos, por encima de lenguajes de propósito general.")

elif seccion == "🌎 Modalidad":
    col1, col2 = st.columns([1, 1.3])
    with col1.container(border=True):
        st.markdown("##### 🏠 Distribución por modalidad")
        st.plotly_chart(g_modalidad(), use_container_width=True)
    with col2.container(border=True):
        st.markdown("##### 📈 Variación de ofertas por mes")
        df = consultar("""
            SELECT t.mes, t.nombre_mes, r.nombre_rol, COUNT(*) AS ofertas
            FROM fact_ofertas_empleo f
            JOIN dim_tiempo t ON f.id_tiempo = t.id_tiempo
            JOIN dim_rol r ON f.id_rol = r.id_rol
            WHERE r.nombre_rol <> 'Otro' AND t.anio = 2026
            GROUP BY t.mes, t.nombre_mes, r.nombre_rol ORDER BY t.mes
        """)
        fig = px.line(df, x="nombre_mes", y="ofertas", color="nombre_rol", markers=True,
                      color_discrete_sequence=PALETA,
                      labels={"nombre_mes": "", "ofertas": "Ofertas", "nombre_rol": ""})
        st.plotly_chart(estilo(fig, leyenda=True), use_container_width=True)

    with st.container(border=True):
        st.markdown("##### 🌍 Modalidad: local vs. internacional")
        df_mi = consultar("""
            SELECT fu.ambito, m.nombre_modalidad,
                   ROUND(100.0*COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY fu.ambito), 1) AS pct
            FROM fact_ofertas_empleo f
            JOIN dim_fuente fu ON f.id_fuente = fu.id_fuente
            JOIN dim_modalidad m ON f.id_modalidad = m.id_modalidad
            GROUP BY fu.ambito, m.nombre_modalidad
        """)
        df_mi["pct"] = df_mi["pct"].astype(float)
        # % de remotas por ambito calculado en vivo (no fijo) para el insight.
        def _pct_remoto(amb):
            fila = df_mi[(df_mi["ambito"] == amb) & (df_mi["nombre_modalidad"] == "Remoto")]
            return float(fila["pct"].iloc[0]) if not fila.empty else 0.0
        r_int, r_loc = _pct_remoto("internacional"), _pct_remoto("local")

        # Etiqueta capitalizada para que la leyenda diga "Local" / "Internacional".
        df_mi["Ámbito"] = df_mi["ambito"].str.capitalize()
        fig = px.bar(df_mi, x="nombre_modalidad", y="pct", color="Ámbito", barmode="group",
                     text_auto=".1f", color_discrete_sequence=PALETA,
                     labels={"nombre_modalidad": "", "pct": "% dentro del ámbito"})
        st.plotly_chart(estilo(fig, leyenda=True), use_container_width=True)
        st.info(f"Las ofertas **internacionales** son mucho más remotas ({r_int}%) que las "
                f"**locales** ({r_loc}%): el teletrabajo en el mercado tecnológico ecuatoriano "
                "sigue siendo marginal. Esto responde la pregunta secundaria 2 del Entregable 1.")
