import streamlit as st
import requests
from datetime import datetime
import os

TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Asistencia Loga", page_icon="🛡️", layout="centered")
query_params = st.query_params
division = query_params.get("div", "No seleccionada")

# --- MOTOR DE BÚSQUEDA AGRESIVO ---
def verificar_bloqueo_absoluto(fecha_sel, div_sel):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    # Forzamos a Notion a filtrar por fecha exacta
    payload = {
        "filter": {
            "and": [
                {"property": "Fecha", "date": {"equals": fecha_sel.strftime("%Y-%m-%d")}},
                {"property": "División", "select": {"equals": div_sel}}
            ]
        }
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        # Si Notion devuelve cualquier resultado, hay asistencia cargada
        return len(res.json().get("results", [])) > 0
    except:
        return False

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

# UI
col_img, col_title = st.columns([1, 4])
with col_img:
    files = [f for f in os.listdir('.') if f.lower().startswith('logo')]
    if files: st.image(files[0], width=80)
with col_title: st.title(f"Loga {division}")

fecha_input = st.date_input("Fecha", datetime.now(), format="DD/MM/YYYY")

# VERIFICACIÓN DE BLOQUEO
bloqueado = verificar_bloqueo_absoluto(fecha_input, division)

if bloqueado:
    st.error("🛑 SISTEMA BLOQUEADO: Ya se registró la asistencia de hoy en Notion.")
    st.warning("No puedes volver a enviar datos para esta división y fecha para evitar duplicados.")
else:
    st.info("✅ Día libre de registros. Puedes proceder con la asistencia.")

st.divider()

jugadores = fetch_jugadores(division)
if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

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

# LÓGICA DE BOTÓN FINAL
if bloqueado:
    # Mostramos el botón pero desactivado y con un mensaje claro
    st.button("ENVÍO DESACTIVADO (YA CARGADO)", use_container_width=True, disabled=True)
else:
    # Solo si NO está bloqueado mostramos el botón real
    if st.button("Enviar asistencia", use_container_width=True, type="primary"):
        with st.spinner("Guardando..."):
            for j in jugadores:
                payload = {
                    "parent": {"database_id": DB_ASISTENCIA},
                    "properties": {
                        "Jugador": {"relation": [{"id": j['id']}]},
                        "Asistencia": {"select": {"name": st.session_state.asistencias[j['nombre']]}},
                        "Fecha": {"date": {"start": fecha_input.strftime("%Y-%m-%d")}},
                        "División": {"select": {"name": division}}
                    }
                }
                requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        st.success("¡Asistencia guardada correctamente!")
