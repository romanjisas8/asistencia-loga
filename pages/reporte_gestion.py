import streamlit as st
import requests
import pandas as pd
import plotly.express as px

TOKEN = st.secrets["NOTION_TOKEN"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Gestión de División", page_icon="📈", layout="wide")

@st.cache_data(ttl=300)
def cargar_datos():
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    all_results = []
    has_more = True
    next_cursor = None
    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        res = requests.post(url, headers=headers, json=payload).json()
        all_results.extend(res.get("results", []))
        has_more = res.get("has_more", False)
        next_cursor = res.get("next_cursor")
    
    data = []
    for row in all_results:
        p = row["properties"]
        # Extraer División (Rollup/Select/Formula)
        div = "S/D"
        p_div = p.get("División", {})
        if p_div.get("type") == "select": div = p_div.get("select", {}).get("name", "S/D")
        elif p_div.get("type") == "rollup":
            arr = p_div.get("rollup", {}).get("array", [])
            if arr: div = arr[0].get("select", {}).get("name", "S/D")
        
        # Extraer Nombre del Jugador de la Relación
        j_rel = p.get("Jugador", {}).get("relation", [])
        j_id = j_rel[0]["id"] if j_rel else "Desconocido"
        # NOTA: Para obtener el nombre real aquí, necesitaríamos consultar la otra DB.
        # Por ahora usaremos el ID o un marcador.
            
        data.append({
            "Fecha": p.get("Fecha", {}).get("date", {}).get("start", ""),
            "Asistencia": p.get("Asistencia", {}).get("select", {}).get("name", ""),
            "División": div,
            "JugadorID": j_id
        })
    return pd.DataFrame(data)

st.title("🛡️ Panel de Gestión por División")

df = cargar_datos()
if not df.empty:
    # Selector único de División
    st.sidebar.header("Control de División")
    divisiones_disponibles = sorted(df['División'].unique())
    div_elegida = st.sidebar.selectbox("Selecciona la División para analizar", options=divisiones_disponibles)
    
    df_div = df[df['División'] == div_elegida].copy()
    df_div['Fecha'] = pd.to_datetime(df_div['Fecha'])

    # --- MÉTRICAS DE LA DIVISIÓN ---
    st.header(f"Estadísticas de {div_elegida}")
    c1, c2, c3 = st.columns(3)
    total_entrenamientos = df_div['Fecha'].nunique()
    promedio_asistencia = (len(df_div[df_div['Asistencia'] == 'Presente']) / len(df_div) * 100) if not df_div.empty else 0
    
    c1.metric("Entrenamientos Realizados", total_entrenamientos)
    c2.metric("Promedio de Asistencia", f"{promedio_asistencia:.1f}%")
    c3.metric("Total Jugadores Registrados", df_div['JugadorID'].nunique())

    st.divider()

    # --- GRÁFICO DE ASISTENCIA ---
    st.subheader("Tendencia de Asistencia (Chicos presentes por día)")
    tendencia = df_div[df_div['Asistencia'] == 'Presente'].groupby('Fecha').size().reset_index(name='Presentes')
    fig = px.bar(tendencia, x='Fecha', y='Presentes', color_discrete_sequence=['#ff4b4b'])
    st.plotly_chart(fig, use_container_width=True)

    # --- RANKING DE COMPROMISO ---
    st.subheader("Top Compromiso (Próximamente con nombres reales)")
    ranking = df_div[df_div['Asistencia'] == 'Presente'].groupby('JugadorID').size().sort_values(ascending=False).reset_index(name='Días Presente')
    st.dataframe(ranking, use_container_width=True)

else:
    st.warning("No hay datos en Notion todavía.")
