import streamlit as st
import requests
import pandas as pd
import plotly.express as px

TOKEN = st.secrets["NOTION_TOKEN"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Gestión Loga", page_icon="🛡️", layout="wide")

@st.cache_data(ttl=300)
def cargar_jugadores_activos():
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        res = requests.post(url, headers=headers, json={}).json()
        activos = {}
        for p in res.get("results", []):
            props = p["properties"]
            estado = props.get("Estado", {}).get("select", {}).get("name", "Activo")
            if estado == "Activo":
                nombre = next((v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"), "S/N")
                activos[p["id"]] = nombre
        return activos
    except: return {}

@st.cache_data(ttl=300)
def cargar_asistencias_filtradas(jugadores_activos):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    all_results = []
    has_more, next_cursor = True, None
    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        res = requests.post(url, headers=headers, json=payload).json()
        all_results.extend(res.get("results", []))
        has_more = res.get("has_more", False)
        next_cursor = res.get("next_cursor")
    
    data = []
    for row in all_results:
        p = row["properties"]
        j_id = p.get("Jugador", {}).get("relation", [{}])[0].get("id")
        
        # FILTRO CRUCIAL: Solo tomamos filas de jugadores que están en nuestra lista de "Activos"
        if j_id in jugadores_activos:
            fecha_raw = p.get("Fecha", {}).get("date", {}).get("start")
            if not fecha_raw: continue
            
            div = (p.get("División", {}).get("select") or {}).get("name", "S/D")
            asistencia = (p.get("Asistencia", {}).get("select") or {}).get("name", "Sin marcar")
            
            data.append({"Fecha": fecha_raw, "Asistencia": asistencia, "División": div, "Jugador": jugadores_activos[j_id]})
    return pd.DataFrame(data)

st.title("🛡️ Gestión por División")

maestro_activos = cargar_jugadores_activos()
df_raw = cargar_asistencias_filtradas(maestro_activos)

if not df_raw.empty:
    divs = sorted(df_raw['División'].unique())
    div_elegida = st.sidebar.selectbox("Seleccionar División", options=divs)
    df_div = df_raw[df_raw['División'] == div_elegida].copy()
    
    if not df_div.empty:
        df_div['Fecha'] = pd.to_datetime(df_div['Fecha'], errors='coerce')
        df_div = df_div.dropna(subset=['Fecha'])

        # Cálculos basados solo en activos
        entrenamientos = df_div['Fecha'].nunique()
        df_presentes = df_div[df_div['Asistencia']=='Presente']
        df_ausentes = df_div[df_div['Asistencia']=='Ausente']
        df_saf = df_div[df_div['Asistencia']=='SAF']
        
        total_marcas = len(df_presentes) + len(df_ausentes) + len(df_saf)

        c1, c2 = st.columns(2)
        c1.metric("Entrenamientos", entrenamientos)
        c2.metric("Promedio Asistencia", f"{(len(df_presentes)/total_marcas*100):.1f}%" if total_marcas > 0 else "0%")

        # Gráfico Anillo
        pie_data = pd.DataFrame({'Estado': ['Presente', 'Ausente', 'SAF'], 
                                 'Cantidad': [len(df_presentes), len(df_ausentes), len(df_saf)]})
        fig = px.pie(pie_data, values='Cantidad', names='Estado', hole=0.5, 
                     color_discrete_map={'Presente': '#800000', 'Ausente': '#1a237e', 'SAF': '#FFFFFF'})
        st.plotly_chart(fig)
        
        # Ranking
        st.subheader("Ranking")
        ranking = df_presentes.groupby('Jugador').size().sort_values(ascending=False).reset_index(name='Presencias')
        st.dataframe(ranking, use_container_width=True)
