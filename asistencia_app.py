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

# --- FUNCIÓN DE VERIFICACIÓN MAESTRA (CON PAGINACIÓN) ---
def verificar_registro_real(fecha_sel, div_sel):
    url = f"https://api.notion.com/v1/databases/{DB_ASISTENCIA}/query"
    fecha_str = fecha_sel.strftime("%Y-%m-%d")
    has_more = True
    next_cursor = None
    
    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        try:
            res = requests.post(url, headers=headers, json=payload)
            data = res.json()
            for row in data.get("results", []):
                # Extraer datos de la fila
                f_notion = row["properties"].get("Fecha", {}).get("date", {}).get("start", "")
                d_notion = row["properties"].get("División", {}).get("select", {}).get("name", "")
                
                # Si coincide fecha y división, el registro EXISTE
                if f_notion == fecha_str and d_notion.upper() == div_sel.upper():
                    return True
            
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")
            if not has_more: break
        except:
            return False
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

# --- INTERFAZ ---
col_img, col_title = st.columns([1, 4])
with col_img:
    files = [f for f in os.listdir('.') if f.lower().startswith('logo')]
    if files: st.image(files[0], width=80)
with col_title: st.title(f"Loga {division}")

fecha_input = st.date_input("Fecha", datetime.now(), format="DD/MM/YYYY")

# VERIFICACIÓN INMEDIATA
existe_ya = verificar_registro_real(fecha_input, division)

if existe_ya:
    st.error(f"⚠️ AVISO: El {fecha_input.strftime('%d/%m/%Y')} ya tiene asistencias para {division}.")

st.divider()

jugadores = fetch_jugadores(division)
if 'asistencias' not in st.session_state:
    st.session_state.asistencias = {j['nombre']: "Ausente" for j in jugadores}

for j in jugadores:
    nombre = j['nombre']
    st.text(nombre)
    st.session_state.asistencias[nombre] = st.radio(nombre, ["Presente", "Ausente", "SAF"], 
        index=1 if st.session_state.asistencias.get(nombre) == "Ausente" else (0 if st.session_state.asistencias.get(nombre) == "Presente" else 2),
        key=f"r_{nombre}_{fecha_input}", label_visibility="collapsed", horizontal=True)
    st.write("---")

resumen = list(st.session_state.asistencias.values())
st.markdown(f"""<div style="display:flex; justify-content:space-around; background:#262730; padding:15px; border-radius:10px; color:white; margin-bottom:20px;">
    <div>Pres: {resumen.count("Presente")}</div><div>Aus: {resumen.count("Ausente")}</div><div>SAF: {resumen.count("SAF")}</div></div>""", unsafe_allow_html=True)

# --- LÓGICA DE BOTÓN CON CONFIRMACIÓN ---
if existe_ya:
    confirmar_duplicado = st.checkbox("Entiendo que ya hay registros y quiero enviar de todas formas")
    if confirmar_duplicado:
        if st.button("ENVIAR ASISTENCIA (DUPLICAR)", use_container_width=True, type="primary"):
            ejecutar_envio = True
    else:
        st.button("ENVIAR (BLOQUEADO POR REGISTRO PREVIO)", use_container_width=True, disabled=True)
else:
    if st.button("Enviar asistencia", use_container_width=True, type="primary"):
        ejecutar_envio = True

if 'ejecutar_envio' in locals():
    with st.spinner("Guardando en Notion..."):
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
    st.success("¡Datos enviados correctamente!"); st.balloons()
