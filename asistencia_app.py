import streamlit as st
import requests
from datetime import datetime
import os

# Configuración de Notion
TOKEN = st.secrets["NOTION_TOKEN"]
DB_JUGADORES = st.secrets["DB_JUGADORES"]
DB_ASISTENCIA = st.secrets["DB_ASISTENCIA"]
headers = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

st.set_page_config(page_title="Asistencia Loga", page_icon="🛡️", layout="centered")

query_params = st.query_params
division = query_params.get("div", "No seleccionada")

# --- FUNCIONES ---
def verificar_registro_previo(fecha_selec, div_selec):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    payload = {
        "filter": {
            "property": "Fecha",
            "date": {"equals": fecha_selec.strftime("%Y-%m-%d")}
        }
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        resultados = res.json().get("results", [])
        for registro in resultados:
            prop_div = registro["properties"].get("División", {}).get("select", {}).get("name", "")
            if prop_div.upper() == div_selec.upper():
                return True
        return False
    except:
        return False

@st.cache_data(ttl=60)
def fetch_jugadores(div):
    if div == "No seleccionada": return []
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        response = requests.post(url, headers=headers, json={})
        jugadores = []
        for page in response.json().get("results", []):
            props = page["properties"]
            nombre = next((v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"), "Sin nombre")
            div_notion = props.get("División", {}).get("select", {}).get("name", "")
            estado = props.get("Estado", {}).get("select", {}).get("name", "Activo")
            if estado == "Activo" and div_notion.upper() == div.upper():
                jugadores.append({"nombre": nombre, "id": page["id"]})
        # ORDEN ALFABÉTICO AQUÍ
        return sorted(jugadores, key=lambda x: x['nombre'])
    except: return []

# --- INTERFAZ ---
col_img, col_title = st.columns([1, 4])
with col_img:
    files = [f for f in os.listdir('.') if f.lower().startswith('logo')]
    if files: st.image(files[0], width=80)
    else: st.write("🛡️")
with col_title: st.title(f"Loga {division}")

if division == "No seleccionada":
    st.error("Accede con ?div=M16")
    st.stop()

# FECHA Y AVISO
fecha_input = st.date_input("Fecha", datetime.now(), format="DD/MM/YYYY")
hay_registro = verificar_registro_previo(fecha_input, division)

if hay_registro:
    st.warning(f"⚠️ AVISO: El día {fecha_input.strftime('%d/%m/%Y')} ya tiene asistencias para {division}.")

st.divider()

jugadores = fetch_jugadores(division)
if not jugadores:
    st.info(f"No se encontraron jugadores activos para {division}.")
    st.stop()

if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

# Lista de jugadores (Ya viene ordenada de la función)
for j in jugadores:
    nombre = j['nombre']
    st.text(nombre)
    st.session_state.asistencias[nombre] = st.radio(nombre, ["Presente", "Ausente", "SAF"], 
        index=1 if st.session_state.asistencias.get(nombre) == "Ausente" else (0 if st.session_state.asistencias.get(nombre) == "Presente" else 2),
        key=f"r_{nombre}_{fecha_input}", label_visibility="collapsed", horizontal=True)
    st.write("---")

# Contador
resumen = list(st.session_state.asistencias.values())
st.markdown(f"""<div style="display:flex; justify-content:space-around; background:#262730; padding:15px; border-radius:10px; color:white; margin-bottom:20px;">
    <div>Pres: {resumen.count("Presente")}</div><div>Aus: {resumen.count("Ausente")}</div><div>SAF: {resumen.count("SAF")}</div></div>""", unsafe_allow_html=True)

# LÓGICA DE ENVÍO
if 'confirmar' not in st.session_state: st.session_state.confirmar = False

if not st.session_state.confirmar:
    if st.button("Enviar asistencia", use_container_width=True, type="primary"):
        if hay_registro:
            st.session_state.confirmar = True
            st.rerun()
        else:
            ejecutar_real = True
else:
    st.error(f"🛑 ATENCIÓN: Ya existen datos cargados. ¿Deseas duplicarlos?")
    c1, col_cancel = st.columns(2)
    if c1.button("SÍ, ENVIAR", use_container_width=True):
        ejecutar_real = True
        st.session_state.confirmar = False
    if col_cancel.button("CANCELAR", use_container_width=True):
        st.session_state.confirmar = False
        st.rerun()

if 'ejecutar_real' in locals() and ejecutar_real:
    with st.spinner("Guardando en Notion..."):
        errores = []
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
            if requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload).status_code != 200:
                errores.append(j['nombre'])
        if not errores: st.success("¡Éxito!"); st.balloons()
        else: st.error("Error en algunos registros.")
