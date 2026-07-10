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

st.set_page_config(page_title="Dashboard Mercado Laboral Tech",
                   page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# Paleta azul monocroma (estilo dashboard corporativo).
AZUL = "#2E6099"
AZUL_OSC = "#1F3D5C"
PALETA = ["#1F4E79", "#3B7DD8", "#7FB2E5", "#B9D4EE", "#2E6DB4", "#5B9BD5"]

st.markdown("""
<style>
#MainMenu, footer, [data-testid="stHeader"] {visibility: hidden;}
.stApp {background:#EEF2F7;}
.block-container {padding-top: 1.1rem; padding-bottom: 1.5rem; max-width: 1400px;}

/* ── Sidebar azul ── */
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {
    background: linear-gradient(180deg, #2E6099 0%, #244B77 100%) !important;}
[data-testid="stSidebar"] * {color: #EAF1F8;}
.nw-brand {background:#1F3D5C; margin:-1.5rem -1rem 1.1rem -1rem; padding:22px 18px; text-align:center;}
.nw-brand h1 {color:#fff; font-size:1.55rem; font-weight:800; margin:0; letter-spacing:1.5px;}
.nw-brand p {color:#A9CCE8; font-size:.72rem; margin:3px 0 0; letter-spacing:.5px;}
.nw-filtros {text-align:center; font-size:1.05rem; font-weight:700; color:#fff; margin:2px 0 12px;
    padding-bottom:9px; border-bottom:1px solid rgba(255,255,255,.18);}
[data-testid="stSidebar"] label {color:#DCE8F4 !important; font-size:.8rem !important; font-weight:600;}
[data-testid="stSidebar"] [data-baseweb="select"] > div {background:#EAF1F8; border:1px solid #6C9BC7;
    border-radius:6px;}
[data-testid="stSidebar"] [data-baseweb="select"] * {color:#1F3D5C !important;}
[data-testid="stSidebar"] .stButton button {width:100%; background:#1F3D5C; color:#fff !important;
    border:none; border-radius:6px; font-weight:700; padding:9px; margin-top:6px;}
[data-testid="stSidebar"] .stButton button:hover {background:#16304a;}
.nw-mini {font-size:.85rem; font-weight:700; color:#fff; margin:18px 0 4px;
    border-top:1px solid rgba(255,255,255,.18); padding-top:14px;}

/* ── Tarjetas KPI (sin icono: numero grande arriba, etiqueta abajo) ── */
.kpi {background:#fff; border:1px solid #E4EAF1; border-radius:14px; padding:18px 20px;
    box-shadow:0 2px 12px rgba(31,61,92,.06); height:116px; display:flex; flex-direction:column;
    justify-content:center;}
.kpi-val {font-size:2.0rem; font-weight:800; color:#1F3D5C; line-height:1.05;}
.kpi-lab {color:#7A8AA0; font-size:.80rem; font-weight:600; margin-top:8px;}

/* ── Contenedores de graficos ── */
[data-testid="stVerticalBlockBorderWrapper"] {background:#fff; border:1px solid #E4EAF1 !important;
    border-radius:14px; box-shadow:0 2px 12px rgba(31,61,92,.05); padding:6px 14px 2px;}
.g-title {font-size:1rem; font-weight:700; color:#1F3D5C; text-align:center; margin:6px 0 2px;}

/* ── Tabs modernos ── */
[data-baseweb="tab-list"] {gap:6px;}
[data-baseweb="tab"] {background:#DCE6F1; border-radius:9px 9px 0 0; padding:9px 22px; font-weight:600;
    color:#5A6B82;}
button[aria-selected="true"][data-baseweb="tab"] {background:#2E6099; color:#fff;}
h1,h2,h3,h4,h5,h6 {color:#1F3D5C;}
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


def estilo(fig, alto=320, leyenda=None):
    # leyenda: None sin leyenda, 'h' horizontal arriba, 'v' vertical a la derecha.
    cfg = dict(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
               plot_bgcolor="rgba(0,0,0,0)", colorway=PALETA,
               font=dict(family="Segoe UI, sans-serif", color="#43506b", size=12.5),
               margin=dict(l=10, r=10, t=30 if leyenda else 16, b=10),
               height=alto, showlegend=leyenda is not None)
    if leyenda == "h":
        cfg["legend"] = dict(orientation="h", y=1.14, x=0, title="")
    elif leyenda == "v":
        cfg["legend"] = dict(orientation="v", y=0.5, x=1.02, title="")
    fig.update_layout(**cfg)
    fig.update_xaxes(gridcolor="rgba(31,61,92,0.06)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(31,61,92,0.06)", zeroline=False)
    return fig


def tarjeta(col, label, valor):
    col.markdown(f'<div class="kpi"><div class="kpi-val">{valor}</div>'
                 f'<div class="kpi-lab">{label}</div></div>', unsafe_allow_html=True)


def titulo(txt):
    st.markdown(f'<div class="g-title">{txt}</div>', unsafe_allow_html=True)


def mostrar(fig):
    if fig is None:
        st.info("Sin datos para los filtros seleccionados.")
    else:
        st.plotly_chart(fig, use_container_width=True)


# Catalogos para los filtros (dimensiones maestras del proyecto).
FUENTES = ["computrabajo", "multitrabajos", "buscojobs", "linkedin", "jooble", "remotive"]
ROLES = ["Desarrollador de Software", "Analista-Cientifico de Datos", "QA Tester", "Otro"]


def limpiar_filtros():
    st.session_state.f_fuente = "Todas"
    st.session_state.f_rol = "Todos"
    st.session_state.f_mes = "Todos"


# ── Sidebar: marca + filtros tipo dropdown + mini grafico ─────────────────────
with st.sidebar:
    st.markdown('<div class="nw-brand"><h1>BI MERCADO TECH</h1>'
                '<p>Mercado Laboral Tecnológico · Ecuador</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="nw-filtros">Filtros</div>', unsafe_allow_html=True)

    meses_disp = consultar(
        "SELECT DISTINCT mes, nombre_mes FROM dim_tiempo ORDER BY mes"
    )["nombre_mes"].tolist()

    fuente_sel = st.selectbox("Fuente", ["Todas"] + FUENTES, key="f_fuente")
    rol_sel = st.selectbox("Rol", ["Todos"] + ROLES, key="f_rol")
    mes_sel = st.selectbox("Mes de publicación", ["Todos"] + meses_disp, key="f_mes")
    st.button("Limpiar Filtros", on_click=limpiar_filtros)


# ── Filtro dinamico: se inyecta en TODAS las consultas (interactividad reactiva) ─
def _cond(campo, valor, todos):
    return f"{campo} = '{valor}'" if valor != todos else None


_c = [c for c in (_cond("fu.nombre_fuente", fuente_sel, "Todas"),
                  _cond("r.nombre_rol", rol_sel, "Todos"),
                  _cond("t.nombre_mes", mes_sel, "Todos")) if c]
F = (" AND " + " AND ".join(_c)) if _c else ""

# Joins que aportan las columnas fu/r/t a cualquier consulta sobre la tabla de hechos.
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


def money_md(v):
    return f"\\${float(v):,.0f}" if v is not None else "n/d"


def pct(v):
    return f"{float(v):g}%" if v is not None else "n/d"


# ── Encabezado ────────────────────────────────────────────────────────────────
st.markdown("## Dashboard del Mercado Laboral Tecnológico")
st.caption("Análisis comparativo de datos heterogéneos · Ecuador 2026")
st.write("")

c = st.columns(6)
tarjeta(c[0], "Total de ofertas", f"{total:,}")
tarjeta(c[1], "Salario local", money(sal_local))
tarjeta(c[2], "Salario internacional", money(sal_intl))
tarjeta(c[3], "Brecha local vs. intl", pct(brecha))
tarjeta(c[4], "Tasa remota", pct(tasa_remota))
tarjeta(c[5], "TI local vs. nacional", f"{relacion}x" if relacion is not None else "n/d")
st.write("")


# ── Consultas de graficos (todas respetan el filtro F) ────────────────────────
def g_mes_area():
    df = consultar(f"""
        SELECT t.mes, t.nombre_mes, COUNT(*) AS ofertas
        FROM fact_ofertas_empleo f {JOINS}
        WHERE r.nombre_rol <> 'Otro' AND t.anio = 2026 {F}
        GROUP BY t.mes, t.nombre_mes ORDER BY t.mes
    """)
    if df.empty:
        return None
    fig = px.area(df, x="nombre_mes", y="ofertas", markers=True,
                  labels={"nombre_mes": "", "ofertas": "Ofertas"})
    fig.update_traces(line_color="#2E6DB4", fillcolor="rgba(59,125,216,0.22)")
    return estilo(fig)


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
    fig = px.pie(df, names="nombre_modalidad", values="ofertas", hole=0.58,
                 color_discrete_sequence=PALETA)
    fig.update_traces(textposition="inside", textinfo="percent")
    return estilo(fig, leyenda="v")


def g_salario_rol():
    df = consultar(f"""
        SELECT r.nombre_rol, ROUND(AVG(f.salario_ofertado), 0) AS prom, COUNT(*) AS n
        FROM fact_ofertas_empleo f {JOINS}
        WHERE f.tiene_salario = 1 AND fu.ambito = 'local' {F}
        GROUP BY r.nombre_rol ORDER BY prom ASC
    """)
    if df.empty:
        return None
    df["prom"] = df["prom"].astype(float)
    df["nombre_rol"] = df["nombre_rol"].replace("Otro", "Otros roles TI")
    df["etq"] = df["nombre_rol"] + " (n=" + df["n"].astype(str) + ")"
    fig = px.bar(df, x="prom", y="etq", orientation="h", text_auto=".0f",
                 labels={"prom": "Salario promedio (USD)", "etq": ""})
    fig.update_traces(marker_color="#3B7DD8")
    return estilo(fig)


def g_tecnologias(alto=320):
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
    fig = px.bar(df.sort_values("pct"), x="pct", y="nombre_tecnologia", orientation="h",
                 text_auto=".1f", labels={"pct": "% de ofertas", "nombre_tecnologia": ""})
    fig.update_traces(marker_color="#1F4E79")
    return estilo(fig, alto)


def g_fuente():
    df = consultar(f"""
        SELECT fu.nombre_fuente, COUNT(*) AS ofertas
        FROM fact_ofertas_empleo f {JOINS}
        WHERE 1=1 {F}
        GROUP BY fu.nombre_fuente ORDER BY ofertas ASC
    """)
    if df.empty:
        return None
    fig = px.bar(df, x="ofertas", y="nombre_fuente", orientation="h", text_auto=True,
                 labels={"ofertas": "N.º de ofertas", "nombre_fuente": ""})
    fig.update_traces(marker_color="#5B9BD5")
    return estilo(fig)


NOTA_SALARIO = ("Promedio sobre ofertas locales que publican salario (muestra reducida). "
                "Analista/Científico de Datos no aparece: ninguna de sus ofertas publicó salario.")

# ── Vistas (multi-vista con pestañas) ─────────────────────────────────────────
tab1, tab2 = st.tabs(["Resumen General", "Análisis Detallado"])

with tab1:
    c1, c2 = st.columns([1.5, 1])
    with c1.container(border=True):
        titulo("Ofertas por mes de publicación")
        mostrar(g_mes_area())
    with c2.container(border=True):
        titulo("Distribución por modalidad")
        mostrar(g_modalidad())

    g1, g2, g3 = st.columns(3)
    with g1.container(border=True):
        titulo("Salario promedio por rol (local)")
        mostrar(g_salario_rol())
        st.caption(NOTA_SALARIO)
    with g2.container(border=True):
        titulo("Top 10 tecnologías demandadas")
        mostrar(g_tecnologias())
    with g3.container(border=True):
        titulo("Ofertas por fuente")
        mostrar(g_fuente())

    if n_sal and relacion is not None:
        st.success(
            f"**Insight principal:** solo el **{pct(pct_sal)}** de las ofertas "
            f"({n_sal} de {total}) publica el salario. Entre las locales que sí lo hacen, "
            f"el promedio ({money_md(sal_local)}) equivale a **{relacion}×** el salario nacional "
            f"del INEC ({money_md(nacional)}) del sector información y comunicación.")

with tab2:
    st.warning(f"**Opacidad salarial:** solo el **{pct(pct_sal)}** de las ofertas "
               f"({n_sal} de {total}) publica el salario; el resto lo declara \"a convenir\". "
               "Los análisis salariales se basan en muestras reducidas y son indicativos.")

    d1, d2 = st.columns(2)
    with d1.container(border=True):
        titulo("Salario promedio: local vs. internacional")
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
                         color_discrete_sequence=PALETA, labels={"etq": "", "prom": "Salario (USD)"})
            st.plotly_chart(estilo(fig), use_container_width=True)

    with d2.container(border=True):
        titulo("Ofertas por mes y rol (evolución)")
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
            st.plotly_chart(estilo(fig, leyenda="h"), use_container_width=True)

    with st.container(border=True):
        titulo("Modalidad de trabajo: local vs. internacional")
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
            st.plotly_chart(estilo(fig, leyenda="h"), use_container_width=True)
            st.info(f"Las ofertas internacionales son mucho más remotas ({r_int:g}%) que las "
                    f"locales ({r_loc:g}%): el teletrabajo en el mercado ecuatoriano sigue siendo "
                    "marginal. Esto responde la pregunta secundaria 2 del Entregable 1.")
