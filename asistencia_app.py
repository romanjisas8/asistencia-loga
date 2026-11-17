import streamlit as st
import requests
from datetime import datetime, timedelta
import os

TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Asistencia Loga", page_icon="🛡️", layout="centered")
query_params = st.query_params
division = query_params.get("div", "No seleccionada")

# --- FUNCIONES DE ANALÍTICA ---
def obtener_alertas(div):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    # Consultamos los últimos registros para analizar rachas
    payload = {
        "sorts": [{"property": "Fecha", "direction": "descending"}],
        "page_size": 100
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        resultados = res.json().get("results", [])
        
        historial = {} # {Nombre: [Estados]}
        for row in resultados:
            p = row["properties"]
            # Verificar división
            d_notion = ""
            p_div = p.get("División", {})
            if p_div.get("type") == "select": d_notion = p_div.get("select", {}).get("name", "")
            elif p_div.get("type") == "rollup":
                arr = p_div.get("rollup", {}).get("array", [])
                if arr: d_notion = arr[0].get("select", {}).get("name", "")
            
            if d_notion.upper() == div.upper():
                # Obtener nombre del jugador de la relación
                rel = p.get("Jugador", {}).get("relation", [])
                if rel:
                    # Nota: Aquí idealmente necesitamos el nombre, pero para la racha usaremos el ID
                    j_id = rel[0]["id"]
                    estado = p.get("Asistencia", {}).get("select", {}).get("name", "")
                    if j_id not in historial: historial[j_id] = []
                    historial[j_id].append(estado)
        
        # Calcular alertas (3 faltas seguidas)
        alerta_nombres = []
        for j_id, estados in historial.items():
            if len(estados) >= 3 and all(e == "Ausente" for e in estados[:3]):
                alerta_nombres.append(j_id)
        return alerta_nombres
    except: return []

# --- MOTOR DE ASISTENCIA (Igual que antes) ---
def obtener_registros_dia(fecha_sel, div_sel):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    payload = {"filter": {"property": "Fecha", "date": {"equals": fecha_sel.strftime("%Y-%m-%d")}}}
    try:
        res = requests.post(url, headers=headers, json=payload)
        resultados = res.json().get("results", [])
        ids_a_borrar = []
        for row in resultados:
            p_div = row["properties"].get("División", {})
            val_div = ""
            if p_div.get("type") == "select": val_div = p_div.get("select", {}).get("name", "")
            elif p_div.get("type") == "rollup":
                arr = p_div.get("rollup", {}).get("array", [])
                if arr: val_div = arr[0].get("select", {}).get("name", "")
            if val_div.upper() == div_sel.upper(): ids_a_borrar.append(row["id"])
        return ids_a_borrar
    except: return []

@st.cache_data(ttl=60)
def fetch_jugadores(div):
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        res = requests.post(url, headers=headers, json={})
        jugadores = []
        for p in res.json().get("results", []):
            props = p["properties"]
            nombre = next((v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"), "Sin nombre")
            d_notion = props.get("División", {}).get("select", {}).get("name", "")
            estado = props.get("Estado", {}).get("select", {}).get("name", "Activo")
            if estado == "Activo" and d_notion.upper() == div.upper():
                jugadores.append({"nombre": nombre, "id": p["id"]})
        return sorted(jugadores, key=lambda x: x['nombre'])
    except: return []

# --- UI ---
col_img, col_title = st.columns([1, 4])
with col_img:
    files = [f for f in os.listdir('.') if f.lower().startswith('logo')]
    if files: st.image(files[0], width=80)
with col_title: st.title(f"Loga {division}")

fecha_input = st.date_input("Fecha", datetime.now(), format="DD/MM/YYYY")

# --- NUEVA SECCIÓN: ALERTAS ---
with st.expander("📊 Ver Alertas de Compromiso", expanded=False):
    alertas_ids = obtener_alertas(division)
    jugadores_maestros = fetch_jugadores(division)
    nombres_alerta = [j['nombre'] for j in jugadores_maestros if j['id'] in alertas_ids]
    
    if nombres_alerta:
        st.error("⚠️ **Faltas consecutivas (3+):**")
        for n in nombres_alerta:
            st.write(f"- {n}")
    else:
        st.success("✅ No hay alertas de inasistencias repetidas.")

# ... (El resto del código de asistencia, bloqueo y borrado se mantiene igual)
