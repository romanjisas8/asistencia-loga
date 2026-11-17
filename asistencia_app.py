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

# --- FUNCIÓN DE VERIFICACIÓN RÁPIDA ---
def hay_asistencia_hoy(fecha_sel, div_sel):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    # Consultamos solo los últimos 50 registros (más que suficiente para detectar hoy)
    payload = {"page_size": 50} 
    try:
        res = requests.post(url, headers=headers, json=payload)
        for row in res.json().get("results", []):
            f = row["properties"].get("Fecha", {}).get("date", {}).get("start", "")
            d = row["properties"].get("División", {}).get("select", {}).get("name", "")
            if f == fecha_sel.strftime("%Y-%m-%d") and d.upper() == div_sel.upper():
                return True
        return False
    except: return False

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

# Interfaz
col_img, col_title = st.columns([1, 4])
with col_img:
    files = [f for f in os.listdir('.') if f.lower().startswith('logo')]
    if files: st.image(files[0], width=80)
with col_title: st.title(f"Loga {division}")

fecha_input = st.date_input("Fecha", datetime.now(), format="DD/MM/YYYY")

# AVISO DE DUPLICADO
ya_existe = hay_asistencia_hoy(fecha_input, division)
if ya_existe:
    st.error(f"🚨 YA EXISTE ASISTENCIA PARA {division} EN ESTA FECHA.")

st.divider()

jugadores = fetch_jugadores(division)
if not jugadores:
    st.warning(f"No se encontraron jugadores para {division}.")
    st.stop()

if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

for j in jugadores:
    n = j['nombre']
    st.text(n)
    st.session_state.asistencias[n] = st.radio(n, ["Presente", "Ausente", "SAF"], 
        index=1 if st.session_state.asistencias.get(n) == "Ausente" else (0 if st.session_state.asistencias.get(n) == "Presente" else 2),
        key=f"r_{n}_{fecha_input}", label_visibility="collapsed", horizontal=True)
    st.write("---")

resumen = list(st.session_state.asistencias.values())
st.markdown(f"""<div style="display:flex; justify-content:space-around; background:#262730; padding:15px; border-radius:10px; color:white; margin-bottom:20px;">
    <div>P: {resumen.count("Presente")}</div><div>A: {resumen.count("Ausente")}</div><div>S: {resumen.count("SAF")}</div></div>""", unsafe_allow_html=True)

# Lógica de Botón
if ya_existe:
    if st.checkbox("Confirmar duplicado"):
        if st.button("ENVIAR DE TODAS FORMAS", use_container_width=True):
            ejecutar = True
else:
    if st.button("Enviar asistencia", use_container_width=True, type="primary"):
        ejecutar = True

if 'ejecutar' in locals():
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
    st.success("¡Enviado!")
