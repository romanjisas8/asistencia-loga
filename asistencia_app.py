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

# Inicializar estado para la confirmación de envío duplicado
if 'confirmar_envio' not in st.session_state:
    st.session_state.confirmar_envio = False

def verificar_registro_previo(fecha, div):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    payload = {"filter": {"and": [{"property": "Fecha", "date": {"equals": fecha.strftime("%Y-%m-%d")}}, {"property": "División", "select": {"equals": div}}]}}
    try:
        res = requests.post(url, headers=headers, json=payload)
        return len(res.json().get("results", [])) > 0
    except: return False

@st.cache_data(ttl=60)
def fetch_jugadores(div):
    if div == "No seleccionada": return []
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        payload = {"filter": {"and": [{"property": "División", "select": {"equals": div}}, {"property": "Estado", "select": {"equals": "Activo"}}]}}
        response = requests.post(url, headers=headers, json=payload)
        return [{"nombre": next((v.get("title", [{}])[0].get("plain_text") for k, v in p["properties"].items() if v["type"] == "title"), "Sin nombre"), "id": p["id"]} for p in response.json().get("results", [])]
    except: return []

# Cabecera e Interfaz
col_img, col_title = st.columns([1, 4])
with col_img:
    files = [f for f in os.path.exists('.') and os.listdir('.') if f.lower().startswith('logo')]
    if files: st.image(files[0], width=80)
with col_title: st.title(f"Loga {division}")

if division == "No seleccionada":
    st.error("Accede con ?div=M16")
    st.stop()

# --- 1. AVISO CERCA DE LA FECHA ---
fecha_input = st.date_input("Fecha", datetime.now(), format="DD/MM/YYYY")
hay_registro = verificar_registro_previo(fecha_input, division)

if hay_registro:
    st.warning(f"⚠️ ATENCIÓN: El {fecha_input.strftime('%d/%m/%Y')} ya tiene registros para {division}.")

st.divider()

jugadores = fetch_jugadores(division)
if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

# Lista de jugadores
for j in jugadores:
    nombre = j['nombre']
    st.text(nombre)
    st.session_state.asistencias[nombre] = st.radio(nombre, ["Presente", "Ausente", "SAF"], 
        index=0 if st.session_state.asistencias.get(nombre) == "Presente" else (1 if st.session_state.asistencias.get(nombre) == "Ausente" else 2),
        key=f"r_{nombre}_{fecha_input}", label_visibility="collapsed", horizontal=True)
    st.write("---")

# Contador
resumen = list(st.session_state.asistencias.values())
st.markdown(f"""<div style="display:flex; justify-content:space-around; background:#262730; padding:15px; border-radius:10px; color:white;">
    <div>Pres: {resumen.count("Presente")}</div><div>Aus: {resumen.count("Ausente")}</div><div>SAF: {resumen.count("SAF")}</div></div>""", unsafe_allow_html=True)

# --- 2. LÓGICA DE ENVÍO CON CONFIRMACIÓN ---
if not st.session_state.confirmar_envio:
    if st.button("Enviar asistencia", use_container_width=True, type="primary"):
        if hay_registro:
            # Activamos el estado de confirmación
            st.session_state.confirmar_envio = True
            st.rerun()
        else:
            ejecutar_envio = True # No hay duplicado, enviamos directo
else:
    # Se muestra cuando hay_registro es True Y ya apretaron el primer botón
    st.error(f"🛑 ¿ESTÁS SEGURO? Ya existen datos para esta división en esta fecha.")
    col1, col2 = st.columns(2)
    if col1.button("SÍ, ENVIAR DUPLICADO", use_container_width=True):
        ejecutar_envio = True
        st.session_state.confirmar_envio = False
    if col2.button("CANCELAR", use_container_width=True):
        st.session_state.confirmar_envio = False
        st.rerun()

# Proceso de guardado real
if 'ejecutar_envio' in locals() and ejecutar_envio:
    with st.spinner("Guardando..."):
        errores = []
        for j in jugadores:
            payload = {"parent": {"database_id": DB_ASISTENCIA}, "properties": {"Jugador": {"relation": [{"id": j['id']}]}, "Asistencia": {"select": {"name": st.session_state.asistencias[j['nombre']]}}, "Fecha": {"date": {"start": fecha_input.strftime("%Y-%m-%d")}}, "División": {"select": {"name": division}}}}
            if requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload).status_code != 200: errores.append(j['nombre'])
        if not errores: st.success("¡Asistencia enviada!")
        else: st.error("Errores en algunos registros.")
