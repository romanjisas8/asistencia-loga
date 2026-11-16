@st.cache_data(ttl=60)
def fetch_jugadores(div):
    if div == "No seleccionada": return []
    url = f"https://api.notion.com/v1/databases/{DB_JUGADORES}/query"
    try:
        # Traemos todo y filtramos localmente ignorando mayúsculas/minúsculas
        response = requests.post(url, headers=headers, json={})
        if response.status_code != 200: return [f"Error Notion ({response.status_code})"]
        
        jugadores = []
        for page in response.json().get("results", []):
            props = page["properties"]
            # Obtener nombre y división
            nombre = next((v.get("title", [{}])[0].get("plain_text") for k, v in props.items() if v["type"] == "title"), "Sin nombre")
            div_notion = props.get("División", {}).get("select", {}).get("name", "")
            estado = props.get("Estado", {}).get("select", {}).get("name", "Activo")
            
            # Comparación inteligente (ignora mayúsculas)
            if estado == "Activo" and div_notion.upper() == div.upper():
                jugadores.append({"nombre": nombre, "id": page["id"]})
        return sorted(jugadores, key=lambda x: x['nombre'])
    except Exception as e: return [f"Error: {str(e)}"]
