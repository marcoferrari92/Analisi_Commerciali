

import xarray
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def analisi_performance_campagne(df_events):

    # NOTA: Cambia il nome della colonna se nel tuo file Excel si chiama diversamente
    colonna_campagna = 'CAMPAGNA' 
    colonna_evento = 'TIPO EVENTO'
    colonna_anagrafica = 'TIPO ANAGRAFICA'
    
    if colonna_campagna not in df_events.columns or colonna_evento not in df_events.columns:
        st.error(f"Colonne richieste non trouvate. Assicurati che nel file ci siano '{colonna_campagna}' e '{colonna_evento}'.")
        return
        
    df_temp = df_events.copy()
    if colonna_anagrafica in df_temp.columns:
        df_temp[colonna_anagrafica] = df_temp[colonna_anagrafica].astype(str).str.upper().str.strip()
    
    # Pulizia dati spuri e standardizzazione campagne
    df_temp = df_temp[~df_temp[colonna_evento].astype(str).isin(['nan', 'None', '', 'NaN'])]
    df_temp = df_temp[~df_temp[colonna_campagna].astype(str).isin(['nan', 'None', '', 'NaN'])]
    df_temp[colonna_campagna] = df_temp[colonna_campagna].str.strip().str.upper() 
    df_temp[colonna_evento] = df_temp[colonna_evento].str.upper().str.strip()
    
    # ---------------------------------------------------------
    # FILTRO: Selezione Target Anagrafica e Attività (CHIAVI UNICHE BLINDATE)
    # ---------------------------------------------------------
    st.write(f"#### Filtri analisi Campagne")
    st.write("")

    col0, col1, col2, col3, col4 = st.columns([0.1, 1.2, 0.2, 1.2, 0.1])

    # Estrazione di tutte le campagne reali a monte per la memoria dello stato
    elenco_campagne_totale = sorted(df_temp[colonna_campagna].unique())

    # Usiamo un nome di stato specifico solo per le campagne
    if "campagne_memoria_stato" not in st.session_state:
        st.session_state.campagne_memoria_stato = elenco_campagne_totale

    with col1:
        scelta_anagrafica_campagne = st.selectbox(
            "Seleziona il target aziendale da analizzare:",
            ["Tutte le anagrafiche", "Clienti", "Lead", "Prospect"],
            key="campagne_select_anagrafica"  # <--- Cambiata e resa unica
        )
        
        if scelta_anagrafica_campagne == "Clienti":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'CLIENTE']
        elif scelta_anagrafica_campagne == "Lead":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'LEAD']
        elif scelta_anagrafica_campagne == "Prospect":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'PROSPECT']
            
        mostra_solo_principali = st.checkbox(
            "Solo attività principali (Telefonato, Visitato, Inviata e-mail)", 
            value=True,
            key="campagne_checkbox_solo_principali"  
        )
        attivita_da_considerare = ['TELEFONATO', 'VISITATO', 'INVIATA MAIL']
        if mostra_solo_principali:
            df_temp = df_temp[df_temp[colonna_evento].isin(attivita_da_considerare)]
    
    with col3:
        elenco_campagne_disponibili = sorted(df_temp[colonna_campagna].unique())
        
        # Recuperiamo i dati dalla memoria di stato specifica delle campagne
        default_campagne = [c for c in st.session_state.campagne_memoria_stato if c in elenco_campagne_disponibili]
        
        if not default_campagne:
            default_campagne = elenco_campagne_disponibili

        campagne_selezionate = st.multiselect(
            "Filtra o isola campagne specifiche:",
            options=elenco_campagne_disponibili,
            default=default_campagne,
            key="campagne_multiselect_nomi_reali"  
        )
        # Salviamo la selezione nello stato specifico delle campagne
        st.session_state.campagne_memoria_stato = campagne_selezionate
        df_filtered = df_temp[df_temp[colonna_campagna].isin(campagne_selezionate)]
        
    if df_filtered.empty:
        st.warning("Nessun dato disponibile con i filtri selezionati.")
        return

    # --- COSTRUZIONE MATRICE PIVOT ---
    pivot_df = pd.crosstab(df_filtered[colonna_campagna], df_filtered[colonna_evento])
    totale_per_campagna = pivot_df.sum(axis=1).sort_values(ascending=False)
    ordine_campagne = list(totale_per_campagna.index)
    pivot_df = pivot_df.reindex(index=ordine_campagne)
    
    # Palette colori fissa per eventi e dinamica soft per campagne
    color_mapping_eventi = {
        'VISITARE': '#ffff00', 'VISITATO': '#ffcc00',       
        'TELEFONARE': '#ff66ff', 'TELEFONATO': '#af7ac5',     
        'INVIARE EMAIL': '#66ff66', 'INVIATA MAIL': '#009900', 'INVIO E-MAIL SFC': '#009900', 
        'PARTECIPAZIONE WEBINAR': '#3498db', 'SOLLECITARE OFFERTA COMMERCIALE': '#2c3e50' 
    }
    palette_qualitativa = px.colors.qualitative.Plotly
    colori_campagne_accesi = {camp: palette_qualitativa[i % len(palette_qualitativa)] for i, camp in enumerate(ordine_campagne)}
    
    def hex_to_rgba_soft(hex_str, alpha=0.20):
        hex_str = hex_str.lstrip('#')
        rgb = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
        return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"
        
    colori_campagne_soft = {camp: hex_to_rgba_soft(colori_campagne_accesi[camp]) for camp in ordine_campagne}

    colori_attivita_soft = {
        'VISITATO': 'rgba(255, 204, 0, 0.20)', 'VISITARE': 'rgba(255, 255, 0, 0.20)',
        'TELEFONATO': 'rgba(175, 122, 197, 0.20)', 'TELEFONARE': 'rgba(255, 102, 255, 0.20)',
        'INVIATA MAIL': 'rgba(0, 153, 0, 0.20)', 'INVIARE EMAIL': 'rgba(102, 255, 102, 0.20)',
        'INVIO E-MAIL SFC': 'rgba(0, 153, 0, 0.20)', 'PARTECIPAZIONE WEBINAR': 'rgba(52, 152, 219, 0.20)',
        'SOLLECITARE OFFERTA COMMERCIALE': 'rgba(44, 62, 80, 0.15)'
    }

    st.divider()
    st.write(f"#### 1. Analisi d'Impatto delle Campagne")
    
    tipo_visualizzazione = st.radio(
        "Seleziona la modalità di analisi:",
        ["Efficacia Attività per Campagna", "Mix Sforzi Interni alla Campagna"],
        horizontal=True,
        key="radio_visualizzazione_speculare_campagne"
    )
    st.write("")

    totali_globali_attivita = pivot_df.sum(axis=0).to_dict()
    ordine_grafico_visuale = ordine_campagne[::-1]

    # =========================================================================
    # MODALITÀ 1: EFFICACIA ATTIVITÀ PER CAMPAGNA (Sincro Tabella 1)
    # =========================================================================
    if tipo_visualizzazione == "Efficacia Attività per Campagna":
        st.caption("Ripartizione percentuale delle singole campagne all'interno del volume totale di ogni attività.")
        
        df_assoluto = pivot_df.T.reset_index().melt(id_vars=colonna_evento, var_name=colonna_campagna, value_name='Conteggio')
        pivot_perc = pivot_df.div(pivot_df.sum(axis=0), axis=1) * 100
        df_long = pivot_perc.T.reset_index().melt(id_vars=colonna_evento, var_name=colonna_campagna, value_name='Percentuale')
        df_long['Conteggio'] = df_assoluto['Conteggio']
        df_long['Totale_Team'] = df_long[colonna_evento].map(totali_globali_attivita)
        df_long['Etichetta'] = df_long['Percentuale'].apply(lambda x: f"<b>{x:.1f}%</b>" if x > 0 else "")

        fig = px.bar(
            df_long, y=colonna_evento, x='Percentuale', color=colonna_campagna, 
            text='Etichetta', barmode='group', orientation='h', 
            color_discrete_map=colori_campagne_accesi,
            custom_data=[colonna_campagna, 'Conteggio', 'Totale_Team']
        )
        fig.update_traces(
            hovertemplate="<b>Attività: %{y}</b><br>Campagna: %{customdata[0]}<br>Eventi Campagna: %{customdata[1]}<br>Totale Attività: %{customdata[2]}<br>Quota: %{x:.1f}%<extra></extra>", 
            textposition="outside", cliponaxis=False, outsidetextfont=dict(color="#2c3e50", size=12)
        )
        fig.update_layout(xaxis=dict(ticksuffix="%"), xaxis_title="Quota (%)", yaxis_title="", height=400)
        st.plotly_chart(fig, use_container_width=True)

        # --- TABELLA 1 STYLED ---
        df_totali_attivita = pivot_df.sum(axis=0)
        righe = []
        for att in pivot_df.columns[::-1]:
            tot = df_totali_attivita[att]
            riga = {"Attività": att, "Totale Eventi": tot}
            for c in ordine_campagne:
                conteggio = pivot_df.loc[c, att]
                quota = (conteggio / tot * 100) if tot > 0 else 0.0
                riga[f"{c} (Ev.)"] = conteggio
                riga[f"{c} (%)"] = f"{quota:.1f}%"
            righe.append(riga)
            
        df_riepilogo_tabella = pd.DataFrame(righe).set_index("Attività")

        def stile_tabella_1(row):
            styles = [''] * len(row)
            attivita_corrente = row.name.upper()
            for i, col in enumerate(row.index):
                if col == "Totale Eventi":
                    colore_vivido = color_mapping_eventi.get(attivita_corrente, 'rgba(200,200,200,0.25)')
                    styles[i] = f"background-color: {colore_vivido}; color: black; font-weight: bold;"
                else:
                    nome_campagna = col.replace(" (Ev.)", "").replace(" (%)", "")
                    colore_soft = colori_campagne_soft.get(nome_campagna, 'rgba(200,200,200,0.15)')
                    styles[i] = f"background-color: {colore_soft}; color: black;"
            return styles

        def stile_indice_tabella_1(index_series):
            return [f"background-color: {color_mapping_eventi.get(idx.upper(), '#rgba(200,200,200,0.25)')}; color: black; font-weight: bold;" for idx in index_series]

        df_styled_1 = df_riepilogo_tabella.style.apply(stile_tabella_1, axis=1).apply_index(stile_indice_tabella_1, axis=0)
        config_colonne_1 = {"Totale Eventi": st.column_config.NumberColumn(format="%d")}
        for c in ordine_campagne:
            config_colonne_1[f"{c} (Ev.)"] = st.column_config.NumberColumn(format="%d")

        st.dataframe(df_styled_1, use_container_width=True, column_config=config_colonne_1)

    # =========================================================================
    # MODALITÀ 2: MIX SFORZI INTERNI ALLA CAMPAGNA (Sincro Tabella 2)
    # =========================================================================
    else:
        st.caption("Volume complessivo di sforzi allocati, evidenziando la composizione interna del mix operativo per ogni campagna.")
        
        df_long = pivot_df.reset_index().melt(id_vars=colonna_campagna, var_name=colonna_evento, value_name='Conteggio')
        df_long.columns = ['Campagna', 'Tipo Evento', 'Conteggio']
        
        pivot_perc_oriz = pivot_df.div(pivot_df.sum(axis=1), axis=0) * 100
        df_perc_long = pivot_perc_oriz.reset_index().melt(id_vars=colonna_campagna, var_name=colonna_evento, value_name='Percentuale')
        df_long['Percentuale'] = df_perc_long['Percentuale']
        df_long['Totale_Team'] = df_long['Tipo Evento'].map(totali_globali_attivita)

        fig = px.bar(
            df_long, y='Campagna', x='Conteggio', color='Tipo Evento', 
            text='Conteggio', barmode='relative', orientation='h', 
            color_discrete_map=color_mapping_eventi, 
            category_orders={'Campagna': ordine_grafico_visuale},
            custom_data=['Tipo Evento', 'Percentuale', 'Totale_Team']
        )
        fig.update_traces(
            hovertemplate="<b>Campagna: %{y}</b><br>Attività: %{customdata[0]}<br>Eventi: %{x}<br>Quota su questa campagna: %{customdata[1]:.1f}%<extra></extra>",
            textposition="inside", insidetextanchor="middle"
        )
        
        totali_camp = pivot_df.sum(axis=1)
        for camp, tot in totali_camp.items():
            if tot > 0:
                fig.add_annotation(
                    y=camp, x=tot, text=f"<b>{tot:.0f}</b>", 
                    showarrow=False, xshift=10, yanchor="middle", xanchor="left",
                    font=dict(color="#2c3e50", size=12)
                )
        fig.update_layout(
            xaxis_title="Numero di Eventi", yaxis_title="", 
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450
        )
        massimo_conteggio = totali_camp.max()
        fig.update_xaxes(range=[0, massimo_conteggio * 1.15] if massimo_conteggio > 0 else [0, 10], showgrid=True, gridcolor='rgba(200,200,200,0.2)')
        st.plotly_chart(fig, use_container_width=True)

        # --- TABELLA 2 STYLED ---
        righe_inv = []
        for c in ordine_campagne:
            tot = totali_camp[c]
            riga = {"Campagna": c, "Totale Sforzo": tot}
            for att in pivot_df.columns:
                conteggio_evento = pivot_df.loc[c, att]
                quota_evento = (conteggio_evento / tot * 100) if tot > 0 else 0.0
                riga[f"{att.strip().capitalize()} (Ev.)"] = conteggio_evento
                riga[f"{att.strip().capitalize()} (%)"] = f"{quota_evento:.1f}%"
            righe_inv.append(riga)
            
        df_riepilogo_invertito = pd.DataFrame(righe_inv).set_index("Campagna")

        # STYLING TABELLA 2: Totale Sforzo acceso col colore del commerciale, colonne delle attività a destra soft
        def stile_tabella_2(row):
            styles = [''] * len(row)
            campagna_corrente = row.name 
            for i, col in enumerate(row.index):
                if col == "Totale Sforzo":
                    colore_vivido = colori_campagne_accesi.get(campagna_corrente, '')
                    styles[i] = f"background-color: {colore_vivido}; color: black; font-weight: bold;"
                else:
                    # Identifichiamo l'attività per assegnare il rispettivo colore soft
                    col_upper = col.upper().replace(" (EV.)", "").replace(" (%)", "").strip()
                    colore_soft = 'rgba(200,200,200,0.15)'
                    for att_chiave, colore_rgb in colori_attivita_soft.items():
                        if att_chiave in col_upper:
                            colore_soft = colore_rgb
                            break
                    # RIGA 266 CORRETTA:
                    styles[i] = f"background-color: {colore_soft}; color: black;"
            return styles