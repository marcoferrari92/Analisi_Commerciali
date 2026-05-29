

def analisi_conversione_preventivi(df, finestra, giorni_scadenza=7):
    
    # 1. SEPARAZIONE DATAFRAME
    preventivi = df[df['TIPOLOGIA DOC.'] == "PREVENTIVO"].copy()
    ordini     = df[df['TIPOLOGIA DOC.'].isin(["ORDINE", "ORDINE APERTO"])].copy()

    if preventivi.empty:
        st.warning("⚠️ Nessun PREVENTIVO trovato!")
        return None

    DATA_riferimento = pd.Timestamp.now().normalize()

    # Raggruppamento per calcolare i totali reali di ogni documento nel database
    totali_database = df.groupby(['ID DOCUMENTO', 'TIPOLOGIA DOC.']).agg({
        'TOTALE': 'sum',
        'QT': 'sum' # 'TRACK ID': 'count' per avere il numero di articoli univoci
    }).reset_index()

    # 2. MATCHING (Assicurati che TOTALE e QT siano inclusi nel lato ordini per attivare i suffissi)
    merged = pd.merge(
        preventivi,
        ordini[['TRACK ID', 'ID DOCUMENTO', 'DATA', 'TIPOLOGIA DOC.', 'QT', 'TOTALE']], # <--- Aggiunto TOTALE qui
        on='TRACK ID',
        how='left',
        suffixes=('_prev', '_ord')
    )
    
    merged['diff_giorni'] = (pd.to_datetime(merged['DATA_ord']) - pd.to_datetime(merged['DATA_prev'])).dt.days

    # 3. DEFINIZIONE STATO E LOGICA "INFO"
    def definisci_stato_documento(group):
        id_ordini_collegati = group['ID DOCUMENTO_ord'].dropna().unique()
        
        # ORA i suffissi esistono perché abbiamo messo le colonne in entrambi i DF del merge
        articoli_prev = group['TRACK ID'].unique()
        nr_articoli_prev = len(articoli_prev)
        qta_prev_totale = group['QT_prev'].sum()
        valore_prev_totale = group['TOTALE_prev'].sum() # <--- Ora questa funzionerà

        if len(id_ordini_collegati) > 0:
            info_ordini = totali_database[totali_database['ID DOCUMENTO'].isin(id_ordini_collegati)]
            totale_economico_ord = info_ordini['TOTALE'].sum()
            qta_totale_ord = info_ordini['QT'].sum()
            
            match_righe = group.dropna(subset=['ID DOCUMENTO_ord'])
            articoli_matchati = match_righe['TRACK ID'].unique()
            nr_articoli_matchati = len(articoli_matchati)

            note = []
            if nr_articoli_matchati < nr_articoli_prev:
                note.append("INCOMPLETO")
            
            if any(match_righe['QT_ord'] < match_righe['QT_prev']):
                note.append("RIDOTTO")

            if totale_economico_ord > (valore_prev_totale + 0.01) or qta_totale_ord > qta_prev_totale:
                note.append("EXTRA")
            
            if len(id_ordini_collegati) > 1:
                note.append("MULTI-TRANCHE")

            info_text = " + ".join(note) if note else "INTEGRALE"
            
            id_ordine_display = ", ".join(id_ordini_collegati.astype(str))
            ultimo_match = group.sort_values('DATA_ord', ascending=False).iloc[0]
            stato = "AGGIUDICATO (CHIUSO)" if ultimo_match['TIPOLOGIA DOC._ord'] == "ORDINE" else "AGGIUDICATO (APERTO)"
            
            return pd.Series([
                stato, ultimo_match['diff_giorni'], id_ordine_display,
                totale_economico_ord, qta_totale_ord, ultimo_match['DATA_ord'], info_text
            ])
        
        return pd.Series([None, None, None, 0.0, 0, pd.NaT, "NESSUN ORDINE"])

    # Aggiorna l'assegnazione delle colonne (aggiungendo INFO alla fine)
    risultati = merged.groupby('ID DOCUMENTO_prev', group_keys=False).apply(definisci_stato_documento).reset_index()
    risultati.columns = ['ID PREVENTIVO_KEY', 'STATO_DETTAGLIO', 'DURATA', 'ID ORDINE', 'TOTALE ORDINE', 'NUM ART ORD', 'DATA ORDINE', 'INFO']


    # 4. CREAZIONE REPORT FINALE
    report_prev = preventivi.groupby('ID DOCUMENTO').agg({
        'DATA': 'first', 
        'CLIENTE': 'first', 
        'CODICE GESTIONALE UTENTE': 'first',
        'TOTALE': 'sum',
        'QT': 'sum'     # 'TRACK ID': 'count' per avere il numero di articoli univoci
    }).reset_index()
    
    report_prev = pd.merge(report_prev, risultati, left_on='ID DOCUMENTO', right_on='ID PREVENTIVO_KEY', how='left')

    # 5. ASSEGNAZIONE STATI TEMPORALI
    def elabora_dati_finali(row):
        giorni_passati = (DATA_riferimento - pd.to_datetime(row['DATA'])).days
        
        # Se è aggiudicato, riportiamo i 3 valori calcolati in precedenza
        if pd.notna(row['ID ORDINE']):
            return pd.Series([row['STATO_DETTAGLIO'], row['DURATA'], row['INFO']])
        
        # Se non è aggiudicato, definiamo i 3 valori temporali
        if giorni_passati > finestra:
            return pd.Series(["PERSO", giorni_passati, "SCADUTO"])
        elif (finestra - giorni_passati) <= giorni_scadenza:
            return pd.Series(["IN SCADENZA", giorni_passati, "SOLLECITARE"])
        else:
            return pd.Series(["IN ATTESA", giorni_passati, "IN CORSO"])

    # --- CORREZIONE QUI: Aggiungi 'INFO' alla lista delle colonne ---
    report_prev[['STATO_FINALE', 'DURATA', 'INFO']] = report_prev.apply(elabora_dati_finali, axis=1)

    # --- VISUALIZZAZIONE GRAFICI ---   
    color_map_stato = {
        "AGGIUDICATO (CHIUSO)": "#4E944F",
        "AGGIUDICATO (APERTO)": "#B4E197",
        "IN SCADENZA": "#FFD700",
        "IN ATTESA": "#A2D2FF",
        "PERSO": "#FF9999"
    }

    r1_c1, r1_c2 = st.columns(2)
    with r1_c1:
        stats_n = report_prev['STATO_FINALE'].value_counts().reset_index()
        fig_pie_n = px.pie(stats_n, values='count', names='STATO_FINALE', 
                          title="Esito per Numero Documenti", hole=0.4, 
                          color='STATO_FINALE', color_discrete_map=color_map_stato)
        fig_pie_n.update_traces(
            textinfo='value+percent', 
            texttemplate='%{value}<br><b>%{percent}<b>'
        )
        fig_pie_n.update_layout(
            title={
                'text': "Esito per Numero Documenti",
                'x': 0.5,               # Posizione orizzontale (0.5 = centro)
                'xanchor': 'center',    # Punto di ancoraggio del testo
                'yanchor': 'top'        # Punto di ancoraggio verticale
            },
            legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"))
        st.plotly_chart(fig_pie_n, use_container_width=True)
        
    with r1_c2:
        stats_val = report_prev.groupby('STATO_FINALE')['TOTALE'].sum().reset_index()
        fig_pie_val = px.pie(stats_val, values='TOTALE', names='STATO_FINALE', 
                            title="Esito per Valore Economico (€)", hole=0.4, 
                            color='STATO_FINALE', color_discrete_map=color_map_stato)
        fig_pie_val.update_traces(
            textinfo='value+percent',
            texttemplate='€%{value:,.2f}<br><b>%{percent}<b>'
        )
        fig_pie_val.update_layout(
            title={
                'text': "Esito per Numero Documenti",
                'x': 0.5,               # Posizione orizzontale (0.5 = centro)
                'xanchor': 'center',    # Punto di ancoraggio del testo
                'yanchor': 'top'        # Punto di ancoraggio verticale
            },
            legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"))
        st.plotly_chart(fig_pie_val, use_container_width=True)

    # --- REGISTRO FINALE (NUOVO ORDINE COLONNE) ---
    st.write("")
    st.write("")
    
    # 1. Preparazione DataFrame con l'ordine richiesto (Aggiunta INFO)
    df_display = report_prev[[
        'DATA', 'DATA ORDINE', 'DURATA', 'STATO_FINALE', 'INFO', # <-- Aggiunta qui
        'CLIENTE', 'CODICE GESTIONALE UTENTE', 'QT', 'NUM ART ORD', 'TOTALE', 'TOTALE ORDINE',
        'ID DOCUMENTO', 'ID ORDINE'
    ]].copy()

    # 2. Ridenominazione
    df_display.columns = [
        'Data Prev.', 'Data Ord.', 'Durata', 'Stato', 'Info', # <-- Aggiunta qui
        'Cliente', 'Utente', 'Q.tà Prev.', 'Q.tà Ord.', 'Tot. Prev.', 'Tot. Ord.', 
        'ID Prev.', 'ID Ord.'
    ]

    # 3. Definizione Ordine Personalizzato degli Stati
    ordine_stati = [
        "IN SCADENZA", 
        "IN ATTESA", 
        "AGGIUDICATO (APERTO)", 
        "AGGIUDICATO (CHIUSO)", 
        "PERSO"
    ]

    # Trasformiamo la colonna 'Stato' in una categoria con l'ordine definito sopra
    df_display['Stato'] = pd.Categorical(
        df_display['Stato'], 
        categories=ordine_stati, 
        ordered=True
    )

    # 4. Visualizzazione con Styler
    st.dataframe(
        # Cambiamo il sort_values per usare 'Stato'
        df_display.sort_values(by=['Stato', 'Data Prev.'], ascending=[True, False]).style.format({
            'Data Prev.': lambda x: pd.to_datetime(x).strftime('%d/%m/%Y'),
            'Data Ord.': lambda x: pd.to_datetime(x).strftime('%d/%m/%Y') if pd.notnull(x) else "-",
            'Tot. Prev.': '{:,.2f} €',
            'Tot. Ord.': '{:,.2f} €',
            'Durata': lambda x: f"{int(x)} gg" if pd.notnull(x) else "-",
            'Q.tà Prev.': '{:,.0f}', 
            'Q.tà Ord.': '{:,.0f}'   
        }).map(colora_stato, subset=['Stato']),
        use_container_width=True, 
        hide_index=True
    )

    st.write("")
    st.write("")
    return report_prev
