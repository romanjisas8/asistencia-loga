if st.button("Enviar asistencia", use_container_width=True, type="primary"):
    errores = []
    # Mostramos un mensaje temporal para saber que está trabajando
    with st.spinner("Conectando con Notion..."):
        for j in jugadores:
            nombre = j['nombre']
            payload = {
                "parent": {"database_id": DB_ASISTENCIA},
                "properties": {
                    "Jugador": {"relation": [{"id": j['id']}]},
                    "Asistencia": {"select": {"name": st.session_state.asistencias[nombre]}},
                    "Fecha": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
                }
            }
            res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
            
            if res.status_code != 200:
                # Esto nos va a decir el error real que devuelve Notion
                error_msg = res.json().get('message', 'Sin mensaje de error')
                errores.append(f"{nombre} (Error {res.status_code}: {error_msg})")
    
    if not errores: 
        st.success("¡Datos enviados!")
    else: 
        st.error("Errores encontrados:")
        for err in errores:
            st.write(err)
