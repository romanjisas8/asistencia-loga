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
        
        # Extraer Fecha con validación estricta
        fecha_raw = p.get("Fecha", {}).get("date", {}).get("start") if p.get("Fecha", {}).get("date") else None
        if not fecha_raw: continue # Ignorar filas sin fecha
            
        # Extraer División (Soporte Select/Rollup)
        div = "S/D"
        p_div = p.get("División", {})
        if p_div.get("type") == "select":
            div = (p_div.get("select") or {}).get("name", "S/D")
        elif p_div.get("type") == "rollup":
            rollup_val = p_div.get("rollup", {}).get("array", [])
            if rollup_val:
                div = rollup_val[0].get("select", {}).get("name", "S/D")
        
        # Extraer Asistencia y Jugador con seguridad
        asistencia = (p.get("Asistencia", {}).get("select") or {}).get("name", "Sin marcar")
        j_rel = p.get("Jugador", {}).get("relation", [])
        j_id = j_rel[0].get("id", "Desconocido") if j_rel else "Sin Vinculo"
            
        data.append({"Fecha": fecha_raw, "Asistencia": asistencia, "División": div, "JugadorID": j_id})
    
    return pd.DataFrame(data)

st.title("🛡️ Gestión por División")

maestro = cargar_maestro_jugadores()
df = cargar_asistencias()

if not df.empty:
    divs = sorted(df['División'].unique())
    div_elegida = st.sidebar.selectbox("Seleccionar División", options=divs)
    df_div = df[df['División'] == div_elegida].copy()
    
    if not df_div.empty:
        # CONVERSIÓN DE FECHA ULTRA-SEGURA (Ignora errores)
        df_div['Fecha'] = pd.to_datetime(df_div['Fecha'], errors='coerce')
        df_div = df_div.dropna(subset=['Fecha']) # Borrar filas que no se pudieron convertir
        
        df_div['Jugador'] = df_div['JugadorID'].map(maestro).fillna("Desconocido")

        c1, c2, c3 = st.columns(3)
        c1.metric("Entrenamientos", df_div['Fecha'].nunique())
        presents = len(df_div[df_div['Asistencia']=='Presente'])
        c2.metric("Promedio Asistencia", f"{(presents/len(df_div)*100):.1f}%" if len(df_div)>0 else "0%")
        c3.metric("Jugadores en Base", df_div['JugadorID'].nunique())

        # Gráfico
        tendencia = df_div[df_div['Asistencia']=='Presente'].groupby('Fecha').size().reset_index(name='P')
        if not tendencia.empty:
            st.plotly_chart(px.bar(tendencia, x='Fecha', y='P', title=f"Asistencia Diaria - {div_elegida}", color_discrete_sequence=['#ff4b4b']), use_container_width=True)

        # Ranking
        st.subheader(f"Ranking de Compromiso ({div_elegida})")
        ranking = df_div[df_div['Asistencia']=='Presente'].groupby('Jugador').size().sort_values(ascending=False).reset_index(name='Presencias')
        st.dataframe(ranking, use_container_width=True)
    else:
        st.info(f"No hay registros para la división {div_elegida}.")
else:
    st.warning("Cargando datos... si esto persiste, verifica que haya asistencias cargadas en Notion.")
