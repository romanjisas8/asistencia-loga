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
def cargar_datos_completos():
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    res = requests.post(url, headers=headers, json={}).json()
    data = []
    for row in res.get("results", []):
        p = row["properties"]
        fecha = p.get("Fecha", {}).get("date", {}).get("start")
        if not fecha: continue
        div = (p.get("División", {}).get("select") or {}).get("name", "S/D")
        asistencia = (p.get("Asistencia", {}).get("select") or {}).get("name", "Sin marcar")
        j_id = p.get("Jugador", {}).get("relation", [{}])[0].get("id", "Sin Vinculo")
        data.append({"Fecha": fecha, "Asistencia": asistencia, "División": div, "JugadorID": j_id})
    return pd.DataFrame(data)

st.title("🛡️ Gestión por División")
df = cargar_datos_completos()

if not df.empty:
    divs = sorted(df['División'].unique())
    div_elegida = st.sidebar.selectbox("Seleccionar División", options=divs)
    df_div = df[df['División'] == div_elegida].copy()
    
    if not df_div.empty:
        df_div['Fecha'] = pd.to_datetime(df_div['Fecha'])
        # Ordenamos para numerar entrenamientos
        fechas_ordenadas = sorted(df_div['Fecha'].unique())
        mapa_nros = {f: i + 1 for i, f in enumerate(fechas_ordenadas)}
        df_div['Nro'] = df_div['Fecha'].map(mapa_nros)
        
        # --- MÉTRICAS HORIZONTALES (Resumen) ---
        entrenamientos = df_div['Fecha'].nunique()
        presentes = len(df_div[df_div['Asistencia']=='Presente'])
        promedio = (presentes / len(df_div) * 100) if len(df_div) > 0 else 0
        promedio_jugadores = (presentes / entrenamientos) if entrenamientos > 0 else 0
        
        st.markdown(f"""
            <div style="display: flex; justify-content: space-around; background: #262730; padding: 15px; border-radius: 10px; color: white;">
                <div style="text-align: center;">Entrenamientos<br><b>{entrenamientos}</b></div>
                <div style="text-align: center;">% Asistencia<br><b>{promedio:.1f}%</b></div>
                <div style="text-align: center;">Jugadores x Entreno<br><b>{promedio_jugadores:.1f}</b></div>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()

        # --- GRÁFICO DE BARRAS (SAF ABAJO) ---
        data_plot = df_div[df_div['Asistencia'].isin(['Presente', 'SAF'])].groupby(['Nro', 'Asistencia']).size().reset_index(name='Cantidad')
        data_plot['Asistencia'] = pd.Categorical(data_plot['Asistencia'], categories=['SAF', 'Presente'], ordered=True)
        
        fig = px.bar(data_plot.sort_values('Asistencia'), x='Nro', y='Cantidad', color='Asistencia',
                     title="Evolución (Presentes arriba, SAF abajo)",
                     color_discrete_map={'Presente': '#800000', 'SAF': '#1a237e'})
        fig.update_layout(barmode='stack', hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos.")
