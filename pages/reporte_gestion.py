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
def cargar_maestro_jugadores():
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    res = requests.post(url, headers=headers, json={}).json()
    return {p["id"]: next((v.get("title", [{}])[0].get("plain_text") for k, v in p["properties"].items() if v["type"] == "title"), "S/N") for p in res.get("results", [])}

@st.cache_data(ttl=300)
def cargar_asistencias():
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
        # Extraer División con seguridad
        div = "S/D"
        p_div = p.get("División", {})
        if p_div.get("type") == "select": div = (p_div.get("select") or {}).get("name", "S/D")
        elif p_div.get("type") == "rollup":
            arr = p_div.get("rollup", {}).get("array", [])
            if arr: div = (arr[0].get("select") or {}).get("name", "S/D")
        
        # Extraer Asistencia con seguridad
        asistencia = (p.get("Asistencia", {}).get("select") or {}).get("name", "Sin marcar")
        
        # Extraer Jugador
        j_rel = p.get("Jugador", {}).get("relation", [])
        j_id = j_rel[0]["id"] if j_rel else "Desconocido"
            
        data.append({
            "Fecha": p.get("Fecha", {}).get("date", {}).get("start", ""),
            "Asistencia": asistencia,
            "División": div,
            "JugadorID": j_id
        })
    return pd.DataFrame(data)

st.title("🛡️ Gestión por División")

maestro = cargar_maestro_jugadores()
df = cargar_asistencias()

if not df.empty:
    divs = sorted(df['División'].unique())
    div_elegida = st.sidebar.selectbox("División", options=divs)
    df_div = df[df['División'] == div_elegida].copy()
    
    # Cruzar con nombres reales
    df_div['Jugador'] = df_div['JugadorID'].map(maestro).fillna("Desconocido")
    df_div['Fecha'] = pd.to_datetime(df_div['Fecha'])

    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Entrenamientos", df_div['Fecha'].nunique())
    c2.metric("Asistencia Promedio", f"{(len(df_div[df_div['Asistencia']=='Presente'])/len(df_div)*100):.1f}%")
    c3.metric("Chicos Activos", df_div['JugadorID'].nunique())

    # Gráfico
    tendencia = df_div[df_div['Asistencia']=='Presente'].groupby('Fecha').size().reset_index(name='P')
    st.plotly_chart(px.bar(tendencia, x='Fecha', y='P', title="Presentes por día"), use_container_width=True)

    # Ranking
    st.subheader("Ranking de Asistencia")
    ranking = df_div[df_div['Asistencia']=='Presente'].groupby('Jugador').size().sort_values(ascending=False).reset_index(name='Presencias')
    st.dataframe(ranking, use_container_width=True)
else:
    st.info("Cargando datos de Notion...")
