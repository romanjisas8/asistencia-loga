import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Configuración (Usa tus secretos)
TOKEN = st.secrets["NOTION_TOKEN"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Gestión Loga", page_icon="🛡️", layout="wide")

@st.cache_data(ttl=300)
def cargar_maestro_jugadores():
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        res = requests.post(url, headers=headers, json={}).json()
        return {p["id"]: next((v.get("title", [{}])[0].get("plain_text") for k, v in p["properties"].items() if v["type"] == "title"), "S/N") for p in res.get("results", [])}
    except: return {}

@st.cache_data(ttl=300)
def cargar_asistencias():
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    all_results = []
    has_more, next_cursor = True, None
    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        try:
            res = requests.post(url, headers=headers, json=payload).json()
            all_results.extend(res.get("results", []))
            has_more = res.get("has_more", False)
            next_cursor = res.get("next_cursor")
        except: has_more = False
    
    data = []
    for row in all_results:
        p = row["properties"]
        fecha_raw = p.get("Fecha", {}).get("date", {}).get("start") if p.get("Fecha", {}).get("date") else None
        if not fecha_raw: continue 
        div = "S/D"
        p_div = p.get("División", {})
        if p_div.get("type") == "select": div = (p_div.get("select") or {}).get("name", "S/D")
        elif p_div.get("type") == "rollup":
            arr = p_div.get("rollup", {}).get("array", [])
            if arr: div = (arr[0].get("select") or {}).get("name", "S/D")
        asistencia = (p.get("Asistencia", {}).get("select") or {}).get("name", "Sin marcar")
        j_rel = p.get("Jugador", {}).get("relation", [])
        j_id = j_rel[0].get("id", "Desconocido") if j_rel else "Sin Vinculo"
        data.append({"Fecha": fecha_raw, "Asistencia": asistencia, "División": div, "JugadorID": j_id})
    return pd.DataFrame(data)

st.title("🛡️ Gestión por División")

maestro = cargar_maestro_jugadores()
df_raw = cargar_asistencias()

if not df_raw.empty:
    divs = sorted(df_raw['División'].unique())
    div_elegida = st.sidebar.selectbox("Seleccionar División", options=divs)
    df_div = df_raw[df_raw['División'] == div_elegida].copy()
    
    if not df_div.empty:
        df_div['Fecha'] = pd.to_datetime(df_div['Fecha'], errors='coerce')
        df_div = df_div.dropna(subset=['Fecha']).sort_values('Fecha')
        df_div['Jugador'] = df_div['JugadorID'].map(maestro).fillna("Desconocido")

        # --- CÁLCULO DE MÉTRICAS ---
        entrenamientos_fechas = df_div['Fecha'].unique()
        presents_df = df_div[df_div['Asistencia'] == 'Presente'].groupby('Fecha').size().reset_index(name='P')
        # Asignar número de entrenamiento (1, 2, 3...)
        presents_df['Nro'] = range(1, len(presents_df) + 1)
        
        entrenamientos = len(entrenamientos_fechas)
        presentes_totales = len(df_div[df_div['Asistencia']=='Presente'])

        col_metrics, col_pie = st.columns([2, 1])
        with col_metrics:
            st.subheader(f"Resumen General: {div_elegida}")
            m1, m2 = st.columns(2)
            m1.metric("Entrenamientos", entrenamientos)
            m1.metric("Jugadores en Base", df_div['JugadorID'].nunique())
            m2.metric("Promedio Asistencia (%)", f"{(presentes_totales/len(df_div)*100):.1f}%" if len(df_div)>0 else "0%")
            m2.metric("Jugadores x Entrenamiento", f"{(presentes_totales / entrenamientos):.1f}" if entrenamientos > 0 else "0")

        with col_pie:
            pie_data = df_div['Asistencia'].value_counts().reset_index()
            pie_data.columns = ['Estado', 'Cantidad']
            fig_pie = px.pie(pie_data, values='Cantidad', names='Estado', hole=0.5, 
                             color='Estado', color_discrete_map={'Presente': '#800000', 'Ausente': '#1a237e', 'SAF': '#FFFFFF'})
            fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)

        st.divider()

        # --- GRÁFICOS DE TENDENCIA ---
        st.subheader("Tendencia de Asistencia (Presentes)")
        tab1, tab2 = st.tabs(["Histórico Anual", "Detalle Último Mes"])

        with tab1:
            # Gráfico Anual por Nro de entrenamiento
            fig_anual = px.bar(presents_df, x='Nro', y='P', 
                               title=f"Evolución Anual - {div_elegida}",
                               labels={'Nro': 'Nro de Entrenamiento', 'P': 'Presentes'},
                               color_discrete_sequence=['#800000'])
            st.plotly_chart(fig_anual, use_container_width=True)

        with tab2:
            # Filtrar último mes
            fecha_limite = datetime.now() - timedelta(days=30)
            presents_mes = presents_df[presents_df['Fecha'] >= fecha_limite]
            if not presents_mes.empty:
                fig_mes = px.bar(presents_mes, x='Fecha', y='P', 
                                 title="Detalle de los últimos 30 días",
                                 labels={'Fecha': 'Día', 'P': 'Presentes'},
                                 color_discrete_sequence=['#800000'])
                st.plotly_chart(fig_mes, use_container_width=True)
            else:
                st.info("No hay entrenamientos en los últimos 30 días.")

        # --- RANKING ---
        st.subheader("Ranking de Compromiso")
        ranking = df_div[df_div['Asistencia']=='Presente'].groupby('Jugador').size().sort_values(ascending=False).reset_index(name='Presencias')
        ranking['% Asistencia'] = (ranking['Presencias'] / entrenamientos * 100).map('{:,.1f}%'.format)
        st.dataframe(ranking, use_container_width=True)

    else:
        st.info(f"No hay registros para {div_elegida}.")
