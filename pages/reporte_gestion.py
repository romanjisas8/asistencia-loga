        # === 4. CÁLCULO ESTADÍSTICO POR JUGADOR (FÓRMULA EXACTA DE NOTION) ===
        df_valid = df_div[df_div['Asistencia'].isin(['Presente', 'Ausente', 'SAF'])]
        
        stats_jugador = df_valid.groupby(['Jugador', 'Asistencia']).size().unstack(fill_value=0).reset_index()
        
        for col in ['Presente', 'Ausente', 'SAF']:
            if col not in stats_jugador.columns:
                stats_jugador[col] = 0
        
        # Denominador = SOLO los registros del jugador (Presente + Ausente + SAF)
        stats_jugador['Total_Registros'] = stats_jugador['Presente'] + stats_jugador['Ausente'] + stats_jugador['SAF']
        
        # Numerador = Presente + SAF (el SAF CUENTA COMO PRESENTE, tal como en Notion)
        stats_jugador['Efectivos'] = stats_jugador['Presente'] + stats_jugador['SAF']
        
        # Fórmula exacta de Notion
        stats_jugador['% Asistencia'] = stats_jugador.apply(
            lambda x: round((x['Efectivos'] / x['Total_Registros'] * 100), 1) if x['Total_Registros'] > 0 else 0, axis=1
        )
