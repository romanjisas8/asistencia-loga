import streamlit as st
import requests
from datetime import datetime
import os

# Configuración
TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Asistencia Loga", page_icon="🛡️", layout="centered")
query_params = st.query_params
division = query_params.get("div", "No seleccionada")

# --- FUNCIONES ---
def obtener_registros_dia(fecha_sel, div_sel):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    payload = {"filter": {"property": "Fecha", "date": {"equals": fecha_sel.strftime("%Y-%m-%d")}}}
    try:
        res = requests.post(url, headers=headers, json=payload)
        resultados = res.json().get("results", [])
        ids = []
        for row in resultados:
            p_div = row["properties"].get("División", {})
            val_div = ""
            if p_div.get("type") == "select": val_div = p_div.get("select", {}).get("name", "")
            elif p_div.get("type") == "rollup":
                arr = p_div.get("rollup", {}).get("array", [])
                if arr: val_div = arr[0].get("select", {}).get("name", "")
            if val_div.upper() == div_sel.upper(): ids.append(row["id"])
        return ids
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

# --- ESTADÍSTICAS EN EL LATERAL ---
def mostrar_estadisticas(div):
    st.sidebar.title("📊 Análisis de Compromiso")
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    payload = {"sorts": [{"property": "Fecha", "direction": "descending"}], "page_size": 100}
    try:
        res = requests.post(url, headers=headers, json=payload)
        data = res.json().get("results", [])
        historial = {}
        for row in data:
            props = row["properties"]
            # Sacar nombre del jugador (título de la relación o ID)
            j_rel = props.get("Jugador", {}).get("relation", [])
            if j_rel:
                j_id = j_rel[0]["id"]
                est = props.get("Asistencia", {}).get("select", {}).get("name", "")
                if j_id not in historial: historial[j_id] = []
                historial[j_id].append(est)
        
        # Alertas de 3 faltas
        alertas = []
        for j_id, estados in historial.items():
            if len(estados) >= 3 and all(e == "Ausente" for e in estados[:3]):
                alertas.append(j_id)
        
        if alertas:
            st.sidebar.error("⚠️ Faltas consecutivas (3+):")
            jugadores_base = fetch_jugadores(div)
            for j in jugadores_base:
                if j['id'] in alertas: st.sidebar.write(f"- {j['nombre']}")
        else:
            st.sidebar.success("✅ Sin alertas de inasistencia.")
    except: st.sidebar.write("Cargando datos...")

# --- UI PRINCIPAL ---
col_img, col_title = st.columns([1, 4])
with col_img:
    files = [f for f in os.listdir('.') if f.lower().startswith('logo')]
    if files: st.image(files[0], width=80)
with col_title: st.title(f"Loga {division}")

if division == "No seleccionada":
    st.error("Accede con ?div=M16 (ejemplo)")
    st.stop()

# Cargar estadísticas en el lateral
mostrar_estadisticas(division)

fecha_input = st.date_input("Fecha", datetime.now(), format="DD/MM/YYYY")
regs_hoy = obtener_registros_dia(fecha_input, division)
bloqueado = len(regs_hoy) > 0

if bloqueado:
    st.error(f"🛑 ASISTENCIA YA REGISTRADA PARA {division}.")
    if st.button("🗑️ BORRAR PARA REACER", use_container_width=True):
        for pid in regs_hoy: requests.patch(f"https://api.notion.com/v1/pages/{pid}", headers=headers, json={"archived": True})
        st.rerun()
else: st.success("✅ Día libre.")

st.divider()
jugadores = fetch_jugadores(division)
if jugadores:
    if 'asistencias' not in st.session_state: st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}
    for j in jugadores:
        n = j['nombre']
        st.text(n)
        st.session_state.asistencias[n] = st.radio(n, ["Presente", "Ausente", "SAF"], 
            index=1 if st.session_state.asistencias.get(n) == "Ausente" else 0,
            key=f"r_{n}_{fecha_input}", label_visibility="collapsed", horizontal=True)
        st.write("---")

    resumen = list(st.session_state.asistencias.values())
    st.markdown(f"""<div style="display:flex; justify-content:space-around; background:#262730; padding:15px; border-radius:10px; color:white; margin-bottom:20px;">
        <div>P: {resumen.count("Presente")}</div><div>A: {resumen.count("Ausente")}</div><div>S: {resumen.count("SAF")}</div></div>""", unsafe_allow_html=True)

    if not bloqueado:
        if st.button("Enviar asistencia", use_container_width=True, type="primary"):
            for j in jugadores:
                p = {"parent": {"database_id": DB_ASISTENCIA}, "properties": {"Jugador": {"relation": [{"id": j['id']}]}, "Asistencia": {"select": {"name": st.session_state.asistencias[j['nombre']]}}, "Fecha": {"date": {"start": fecha_input.strftime("%Y-%m-%d")}}, "División": {"select": {"name": division}}}}
                requests.post("https://api.notion.com/v1/pages", headers=headers, json=p)
            st.success("¡Enviado!")
