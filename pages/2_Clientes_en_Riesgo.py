import streamlit as st
import pandas as pd
import plotly.express as px

from utils.filtros import cargar_datos

st.title("Clientes en Riesgo - Medellin")
st.caption("Importaciones MDE filtradas por servicio/estado")

with st.sidebar:
    st.markdown("### Parametros")
    umbral_inactividad = st.slider(
        "Umbral inactividad (dias)",
        min_value=90,
        max_value=365,
        value=180,
        step=30,
        help="Clientes por encima de este valor pasan a riesgo alto/perdido.",
    )

try:
    df_f, ops = cargar_datos()
except FileNotFoundError:
    st.error("No se encontro el archivo en: data/datos_finales.parquet")
    st.stop()

anos_disponibles = sorted(ops["Año"].dropna().unique().astype(int))
with st.sidebar:
    anos_sel = st.multiselect("Filtrar anos", anos_disponibles, default=anos_disponibles)

if not anos_sel:
    st.warning("Selecciona al menos un ano para mostrar resultados.")
    st.stop()

ops = ops[ops["Año"].isin(anos_sel)].copy()
if ops.empty:
    st.info("No hay operaciones para los filtros seleccionados.")
    st.stop()

hoy = pd.Timestamp.today().normalize()

client_stats = (
    ops.groupby("Cliente")
    .agg(
        total_compras=("FileID", "count"),
        ultima_compra=("Fecha Inicio", "max"),
    )
    .reset_index()
)
client_stats["dias_inactivo"] = (hoy - client_stats["ultima_compra"]).dt.days

ultimo_comercial = (
    ops.sort_values("Fecha Inicio")
    .groupby("Cliente")["Comercial Reponsable"]
    .last()
    .reset_index()
    .rename(columns={"Comercial Reponsable": "Ultimo Comercial"})
)

servicios_cliente = (
    ops.groupby("Cliente")["Servicio"]
    .agg(lambda x: ", ".join(sorted(x.dropna().unique())))
    .reset_index()
    .rename(columns={"Servicio": "Servicios Usados"})
)

tabla_riesgo = (
    client_stats
    .merge(ultimo_comercial, on="Cliente", how="left")
    .merge(servicios_cliente, on="Cliente", how="left")
)


def nivel_riesgo(dias):
    if dias <= 90:
        return "Bajo"
    if dias <= umbral_inactividad:
        return "Medio"
    if dias <= umbral_inactividad * 1.5:
        return "Alto"
    return "Perdido"


tabla_riesgo["Riesgo"] = tabla_riesgo["dias_inactivo"].apply(nivel_riesgo)
tabla_riesgo["Ultima Compra"] = tabla_riesgo["ultima_compra"].dt.strftime("%d/%m/%Y")

solo_activos = tabla_riesgo[tabla_riesgo["dias_inactivo"] <= umbral_inactividad].copy()
solo_activos = solo_activos.sort_values("dias_inactivo", ascending=False)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Clientes totales", f"{tabla_riesgo['Cliente'].nunique():,}")
with c2:
    st.metric("Clientes activos", f"{solo_activos['Cliente'].nunique():,}")
with c3:
    st.metric("En riesgo/perdidos", f"{(tabla_riesgo['Cliente'].nunique() - solo_activos['Cliente'].nunique()):,}")

st.markdown("### Clientes activos ordenados por riesgo")
st.dataframe(
    solo_activos[
        [
            "Riesgo",
            "Cliente",
            "total_compras",
            "dias_inactivo",
            "Ultima Compra",
            "Ultimo Comercial",
            "Servicios Usados",
        ]
    ].rename(
        columns={
            "total_compras": "Num Compras",
            "dias_inactivo": "Dias sin comprar",
        }
    ),
    use_container_width=True,
    height=380,
)

col_r1, col_r2 = st.columns(2)

with col_r1:
    st.markdown("#### Dias inactivo vs historial de compras")
    fig_scatter = px.scatter(
        solo_activos,
        x="dias_inactivo",
        y="total_compras",
        text="Cliente",
        color="Riesgo",
        color_discrete_map={
            "Bajo": "#10b981",
            "Medio": "#f59e0b",
            "Alto": "#f97316",
            "Perdido": "#ef4444",
        },
        labels={"dias_inactivo": "Dias sin comprar", "total_compras": "Num Compras"},
        size="total_compras",
        size_max=30,
    )
    fig_scatter.update_traces(textposition="top center", textfont_size=8)
    fig_scatter.add_vline(
        x=umbral_inactividad,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text=f"Umbral {umbral_inactividad}d",
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with col_r2:
    st.markdown("#### Distribucion por nivel de riesgo")
    riesgo_counts = tabla_riesgo["Riesgo"].value_counts().reset_index()
    riesgo_counts.columns = ["Riesgo", "Clientes"]
    fig_pie = px.pie(
        riesgo_counts,
        names="Riesgo",
        values="Clientes",
        color="Riesgo",
        color_discrete_map={
            "Bajo": "#10b981",
            "Medio": "#f59e0b",
            "Alto": "#f97316",
            "Perdido": "#ef4444",
        },
        hole=0.45,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("### Top 10 clientes activos con mayor riesgo de fuga")
top10_riesgo = solo_activos.nlargest(10, "dias_inactivo")[
    ["Riesgo", "Cliente", "total_compras", "dias_inactivo", "Ultimo Comercial"]
].rename(columns={"total_compras": "Num Compras", "dias_inactivo": "Dias sin comprar"})
st.dataframe(top10_riesgo, use_container_width=True)
