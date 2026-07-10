import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
from dotenv import load_dotenv

# Conexion al DW. En local se lee del .env; en Streamlit Cloud, de st.secrets.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _cfg(clave, defecto=None):
    # Prioriza st.secrets (nube) y cae al .env (local) si no existe.
    try:
        if clave in st.secrets:
            return st.secrets[clave]
    except Exception:
        pass
    return os.getenv(clave, defecto)


CONEXION = {
    "host": _cfg("DB_HOST", "localhost"),
    "port": _cfg("DB_PORT", "5432"),
    "dbname": _cfg("DB_NAME", "proyecto_bi_dw"),
    "user": _cfg("DB_USER", "postgres"),
    "password": _cfg("DB_PASSWORD"),
    "sslmode": _cfg("DB_SSLMODE", "prefer"),  # 'require' en la nube (Neon), 'prefer' en local
}

st.set_page_config(page_title="BI - Mercado Laboral Tech Ecuador",
                   page_icon="📊", layout="wide", initial_sidebar_state="expanded")

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
/* Filtros del sidebar legibles */
[data-testid="stSidebar"] hr {border-color: rgba(255,255,255,.15); margin: 12px 0;}
[data-testid="stSidebar"] [data-baseweb="select"] > div {background:#25507d; border-color:rgba(255,255,255,.2);}
[data-testid="stSidebar"] [data-baseweb="tag"] {background:#F5A623 !important;}
[data-testid="stSidebar"] [data-baseweb="tag"] span {color:#1B2A41 !important;}
/* Tarjetas de metricas */
.mcard {background:#fff; border-radius:16px; padding:16px 16px;
    box-shadow:0 4px 16px rgba(27,42,65,.08); height:112px;}
.mcard.dark {background: linear-gradient(135deg, #1B3A5B 0%, #265080 100%);}
.mcard.dark .mcard-label {color:#C5D4E6;}
.mcard.dark .mcard-val {color:#fff;}
.mcard-top {display:flex; justify-content:space-between; align-items:center;}
.mcard-label {color:#7A8AA0; font-size:.70rem; font-weight:700; text-transform:uppercase;
    letter-spacing:.3px; line-height:1.1;}
.mcard-ic {font-size:1.2rem;}
.mcard-val {font-size:1.6rem; font-weight:800; color:#1B3A5B; margin-top:10px;}
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


def mostrar(fig):
    # Dibuja el grafico o avisa si los filtros dejaron el conjunto vacio.
    if fig is None:
        st.info("Sin datos para los filtros seleccionados.")
    else:
        st.plotly_chart(fig, use_container_width=True)


# Catalogos para los filtros (fijos: son las dimensiones maestras del proyecto).
FUENTES = ["computrabajo", "multitrabajos", "buscojobs", "linkedin", "jooble", "remotive"]
ROLES = ["Desarrollador de Software", "Analista-Cientifico de Datos", "QA Tester", "Otro"]

# ── Sidebar: marca + navegacion + filtros ─────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="brand"><div class="brand-logo">📊</div>'
                '<div class="brand-name">BI Mercado Tech</div>'
                '<div class="brand-sub">Ecuador · Entregable 5</div></div>',
                unsafe_allow_html=True)
    seccion = st.radio("Navegación",
                       ["📈 Resumen", "💰 Salarios", "🛠️ Tecnologías", "🌎 Modalidad"],
                       label_visibility="collapsed")
    st.markdown("---")
    st.markdown("**🔎 Filtros**")
    meses_disp = consultar(
        "SELECT DISTINCT mes, nombre_mes FROM dim_tiempo ORDER BY mes"
    )["nombre_mes"].tolist()
    fuentes_sel = st.multiselect("Fuente", FUENTES, default=FUENTES)
    roles_sel = st.multiselect("Rol", ROLES, default=ROLES)
    meses_sel = st.multiselect("Mes de publicación", meses_disp, default=meses_disp)


# ── Filtro dinamico: se inyecta en TODAS las consultas (interactividad reactiva) ─
def _lista(vals):
    return ",".join("'" + str(v).replace("'", "''") + "'" for v in vals)


if not (fuentes_sel and roles_sel and meses_sel):
    F = " AND 1=0"   # si se deselecciona todo de alguna dimension, no hay datos
else:
    _c = []
    if len(fuentes_sel) < len(FUENTES):
        _c.append(f"fu.nombre_fuente IN ({_lista(fuentes_sel)})")
    if len(roles_sel) < len(ROLES):
        _c.append(f"r.nombre_rol IN ({_lista(roles_sel)})")
    if len(meses_sel) < len(meses_disp):
        _c.append(f"t.nombre_mes IN ({_lista(meses_sel)})")
    F = (" AND " + " AND ".join(_c)) if _c else ""

# Joins que aportan las columnas fu/r/t (fuente, rol, tiempo) a cualquier consulta
# sobre la tabla de hechos. Son relaciones muchos-a-uno, no multiplican filas.
JOINS = ("JOIN dim_fuente fu ON f.id_fuente = fu.id_fuente "
         "JOIN dim_rol r ON f.id_rol = r.id_rol "
         "JOIN dim_tiempo t ON f.id_tiempo = t.id_tiempo")


def escalar(sql):
    df = consultar(sql)
    return df.iloc[0, 0] if not df.empty else None


# ── Metricas: 6 KPIs, todas con el filtro aplicado ────────────────────────────
total = int(escalar(f"SELECT COUNT(*) FROM fact_ofertas_empleo f {JOINS} WHERE 1=1 {F}") or 0)
sal_local = escalar(f"SELECT ROUND(AVG(f.salario_ofertado),0) FROM fact_ofertas_empleo f {JOINS} "
                    f"WHERE f.tiene_salario=1 AND fu.ambito='local' {F}")
sal_intl = escalar(f"SELECT ROUND(AVG(f.salario_ofertado),0) FROM fact_ofertas_empleo f {JOINS} "
                   f"WHERE f.tiene_salario=1 AND fu.ambito='internacional' {F}")
tasa_remota = escalar(f"SELECT ROUND(100.0*SUM(es_remota)/NULLIF(COUNT(*),0),1) "
                      f"FROM fact_ofertas_empleo f {JOINS} WHERE 1=1 {F}")
nacional = escalar(f"SELECT MAX(t.salario_promedio_nacional) FROM fact_ofertas_empleo f {JOINS} WHERE 1=1 {F}")
pct_sal = escalar(f"SELECT ROUND(100.0*SUM(tiene_salario)/NULLIF(COUNT(*),0),1) "
                  f"FROM fact_ofertas_empleo f {JOINS} WHERE 1=1 {F}")
n_sal = int(escalar(f"SELECT SUM(tiene_salario) FROM fact_ofertas_empleo f {JOINS} WHERE 1=1 {F}") or 0)

relacion = round(float(sal_local) / float(nacional), 2) if sal_local and nacional else None
brecha = round(100.0 * (float(sal_intl) - float(sal_local)) / float(sal_local)) if sal_local and sal_intl else None


def money(v):
    return f"${float(v):,.0f}" if v is not None else "n/d"


def pct(v):
    return f"{float(v):g}%" if v is not None else "n/d"


def money_md(v):
    # Igual que money() pero escapando el "$" para que Streamlit no lo lea como LaTeX.
    return f"\\${float(v):,.0f}" if v is not None else "n/d"


# ── Encabezado + tarjetas de metricas ─────────────────────────────────────────
st.markdown("### Mercado Laboral Tech en Ecuador")
st.caption("Plataforma de Inteligencia de Negocios · Análisis comparativo de datos heterogéneos")
st.write("")

c = st.columns(6)
metrica(c[0], "Total de ofertas", f"{total}", "📋", dark=True)
metrica(c[1], "Salario local", money(sal_local), "💵")
metrica(c[2], "Salario internacional", money(sal_intl), "🌎")
metrica(c[3], "Brecha local vs. intl", pct(brecha), "↔️")
metrica(c[4], "Tasa remota", pct(tasa_remota), "🏠")
metrica(c[5], "TI local vs. nacional", f"{relacion}x" if relacion is not None else "n/d", "⭐")
st.write("")


# ── Helpers de consultas de cada grafico (todos respetan el filtro F) ──────────
def g_salario_rol():
    # KPI 1 - salario promedio por rol (AVG), solo ofertas locales con salario.
    df = consultar(f"""
        SELECT r.nombre_rol, ROUND(AVG(f.salario_ofertado), 0) AS prom, COUNT(*) AS n
        FROM fact_ofertas_empleo f {JOINS}
        WHERE f.tiene_salario = 1 AND fu.ambito = 'local' {F}
        GROUP BY r.nombre_rol ORDER BY prom DESC
    """)
    if df.empty:
        return None
    df["prom"] = df["prom"].astype(float)
    df["nombre_rol"] = df["nombre_rol"].replace("Otro", "Otros roles de TI")
    df["etq"] = df["nombre_rol"] + " (n=" + df["n"].astype(str) + ")"
    fig = px.bar(df, x="etq", y="prom", text_auto=".0f", color="nombre_rol",
                 color_discrete_sequence=PALETA,
                 labels={"etq": "", "prom": "Salario promedio (USD)"})
    return estilo(fig)


def g_tecnologias(alto=340):
    # KPI 3 - indice de demanda: (menciones / total de ofertas filtradas) * 100.
    df = consultar(f"""
        SELECT tec.nombre_tecnologia,
               ROUND(100.0*COUNT(*) / NULLIF((
                   SELECT COUNT(*) FROM fact_ofertas_empleo f {JOINS} WHERE 1=1 {F}
               ), 0), 1) AS pct
        FROM puente_oferta_tecnologia p
        JOIN fact_ofertas_empleo f ON p.id_oferta = f.id_oferta {JOINS}
        JOIN dim_tecnologia tec ON p.id_tecnologia = tec.id_tecnologia
        WHERE 1=1 {F}
        GROUP BY tec.nombre_tecnologia ORDER BY pct DESC LIMIT 10
    """)
    if df.empty:
        return None
    df["pct"] = df["pct"].astype(float)
    fig = px.bar(df.sort_values("pct"), x="pct", y="nombre_tecnologia",
                 orientation="h", text_auto=".1f",
                 labels={"pct": "% de ofertas que la mencionan", "nombre_tecnologia": ""})
    fig.update_traces(marker_color="#1B3A5B")
    return estilo(fig, alto)


def g_modalidad():
    df = consultar(f"""
        SELECT m.nombre_modalidad, COUNT(*) AS ofertas
        FROM fact_ofertas_empleo f {JOINS}
        JOIN dim_modalidad m ON f.id_modalidad = m.id_modalidad
        WHERE 1=1 {F}
        GROUP BY m.nombre_modalidad ORDER BY ofertas DESC
    """)
    if df.empty:
        return None
    fig = px.pie(df, names="nombre_modalidad", values="ofertas", hole=0.55,
                 color_discrete_sequence=PALETA)
    fig.update_traces(textposition="outside", textinfo="percent+label")
    return estilo(fig)


NOTA_SALARIO = ("ℹ️ Promedio sobre ofertas locales que publican salario (muestra reducida). "
                "Analista/Científico de Datos no aparece: ninguna de sus ofertas publicó salario.")

# ── Contenido segun la seccion elegida ────────────────────────────────────────
if seccion == "📈 Resumen":
    col1, col2 = st.columns([1.3, 1])
    with col1.container(border=True):
        st.markdown("##### 💰 Salario promedio por rol (Ecuador)")
        mostrar(g_salario_rol())
        st.caption(NOTA_SALARIO)
    with col2.container(border=True):
        st.markdown("##### 🏠 Modalidad de trabajo")
        mostrar(g_modalidad())
    with st.container(border=True):
        st.markdown("##### 🛠️ Tecnologías más demandadas")
        mostrar(g_tecnologias(380))
    if n_sal and relacion is not None:
        st.success(
            f"🔎 **Insight principal:** solo el **{pct(pct_sal)}** de las ofertas "
            f"({n_sal} de {total}) publica el salario. Entre las locales que sí lo hacen, "
            f"el promedio ({money_md(sal_local)}) equivale a **{relacion}×** el salario nacional "
            f"del INEC ({money_md(nacional)}) del sector información y comunicación.")

elif seccion == "💰 Salarios":
    st.warning(f"🔍 **Hallazgo — opacidad salarial:** solo el **{pct(pct_sal)}** de las ofertas "
               f"({n_sal} de {total}) publica el salario; el resto lo declara \"a convenir\". Por "
               "eso los análisis salariales se basan en muestras reducidas y se interpretan como "
               "indicativos.")
    col1, col2 = st.columns(2)
    with col1.container(border=True):
        st.markdown("##### 💰 Salario promedio por rol (Ecuador)")
        mostrar(g_salario_rol())
        st.caption(NOTA_SALARIO)
    with col2.container(border=True):
        st.markdown("##### 🌎 Salario local vs. internacional")
        df = consultar(f"""
            SELECT fu.ambito, ROUND(AVG(f.salario_ofertado), 0) AS prom, COUNT(*) AS n
            FROM fact_ofertas_empleo f {JOINS}
            WHERE f.tiene_salario = 1 {F}
            GROUP BY fu.ambito
        """)
        if df.empty:
            st.info("Sin datos para los filtros seleccionados.")
        else:
            df["prom"] = df["prom"].astype(float)
            df["ambito"] = df["ambito"].str.capitalize()
            df["etq"] = df["ambito"] + " (n=" + df["n"].astype(str) + ")"
            fig = px.bar(df, x="etq", y="prom", text_auto=".0f", color="ambito",
                         color_discrete_sequence=PALETA,
                         labels={"etq": "", "prom": "Salario promedio (USD)"})
            st.plotly_chart(estilo(fig), use_container_width=True)
    with st.container(border=True):
        st.markdown("##### 📋 Completitud de los datos (global)")
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
        mostrar(g_tecnologias(440))
    st.info("**SQL** y **Python** lideran la demanda, lo que refleja un mercado orientado a la "
            "gestión y el análisis de datos, por encima de lenguajes de propósito general.")

elif seccion == "🌎 Modalidad":
    col1, col2 = st.columns([1, 1.3])
    with col1.container(border=True):
        st.markdown("##### 🏠 Distribución por modalidad")
        mostrar(g_modalidad())
    with col2.container(border=True):
        st.markdown("##### 📈 Ofertas por mes de publicación")
        df = consultar(f"""
            SELECT t.mes, t.nombre_mes, r.nombre_rol, COUNT(*) AS ofertas
            FROM fact_ofertas_empleo f {JOINS}
            WHERE r.nombre_rol <> 'Otro' AND t.anio = 2026 {F}
            GROUP BY t.mes, t.nombre_mes, r.nombre_rol ORDER BY t.mes
        """)
        if df.empty:
            st.info("Sin datos para los filtros seleccionados.")
        else:
            fig = px.line(df, x="nombre_mes", y="ofertas", color="nombre_rol", markers=True,
                          color_discrete_sequence=PALETA,
                          labels={"nombre_mes": "", "ofertas": "Ofertas", "nombre_rol": ""})
            st.plotly_chart(estilo(fig, leyenda=True), use_container_width=True)

    with st.container(border=True):
        st.markdown("##### 🌍 Modalidad: local vs. internacional")
        df_mi = consultar(f"""
            SELECT fu.ambito, m.nombre_modalidad,
                   ROUND(100.0*COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY fu.ambito), 1) AS pct
            FROM fact_ofertas_empleo f {JOINS}
            JOIN dim_modalidad m ON f.id_modalidad = m.id_modalidad
            WHERE 1=1 {F}
            GROUP BY fu.ambito, m.nombre_modalidad
        """)
        if df_mi.empty:
            st.info("Sin datos para los filtros seleccionados.")
        else:
            df_mi["pct"] = df_mi["pct"].astype(float)

            def _pct_remoto(amb):
                fila = df_mi[(df_mi["ambito"] == amb) & (df_mi["nombre_modalidad"] == "Remoto")]
                return float(fila["pct"].iloc[0]) if not fila.empty else 0.0
            r_int, r_loc = _pct_remoto("internacional"), _pct_remoto("local")

            df_mi["Ámbito"] = df_mi["ambito"].str.capitalize()
            fig = px.bar(df_mi, x="nombre_modalidad", y="pct", color="Ámbito", barmode="group",
                         text_auto=".1f", color_discrete_sequence=PALETA,
                         labels={"nombre_modalidad": "", "pct": "% dentro del ámbito"})
            st.plotly_chart(estilo(fig, leyenda=True), use_container_width=True)
            st.info(f"Las ofertas **internacionales** son mucho más remotas ({r_int:g}%) que las "
                    f"**locales** ({r_loc:g}%): el teletrabajo en el mercado tecnológico ecuatoriano "
                    "sigue siendo marginal. Esto responde la pregunta secundaria 2 del Entregable 1.")
