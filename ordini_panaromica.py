import streamlit as st
import pandas as pd
import plotly.express as px


def mostra_panoramica_ordini(df_ordini, df_aperti):


    # DIZIONARIO COLORI (quello che avevi definito all'inizio)
    COLORI_VOCI = {
        'PREV. PERSI': '#ff9999',         # Rosso
        'PREV. IN ATTESA': '#ffff99',     # Giallo
        'PREV. VINTI': '#80e680',         # Verde chiaro
        'ORD. VINTI': '#80e680',         # Verde chiaro
        'ORD. ORFANI': '#e9e9e9',         # Grigio chiaro
        'ACQUISTI DIRETTI': '#555555',    # Grigio scuro
        'CHPR ORFANI': '#ff3333',         # Rosso
        'CHPR': '#ff3333',                # Rosso (gestione decurtazioni)
        'ALTRI': '#80bfff'                # Blu
    }

    # Funzione che applica il colore alla riga in base alla colonna VOCE
    def colora_righe(row):
        voce = row['VOCE']
        colore = COLORI_VOCI.get(voce, '#ffffff') # Bianco di default
        return [f'background-color: {colore}'] * len(row)
    

    # Funzione di aggregazione dedicata
    def calcola_riepilogo(df_sub, is_ordine):

        # Ordini
        if is_ordine:
            df_aggr = df_sub.groupby('ID_FAMIGLIA').agg({
                'TOTALE_RIGA': 'sum',
                'VOCE': 'first' 
            })
            
        # Prevetivi
        else:
            # Per i preventivi: ogni riga (ID_DOC) è una revisione distinta, non sommiamo
            df_aggr = df_sub.groupby('ID_DOC').agg({
                'TOTALE_RIGA': 'sum',
                'VOCE': 'first'
            })
        
        # Creazione tabella pivot
        pivot = df_aggr.groupby('VOCE').agg(
            N_DOCUMENTI=('VOCE', 'count'),
            IMPORTO_TOT=('TOTALE_RIGA', 'sum')
        ).reset_index()
        
        # Calcolo quote
        tot_doc = pivot['N_DOCUMENTI'].sum()
        tot_imp = pivot['IMPORTO_TOT'].sum()
        pivot['QUOTA_DOC (%)'] = (pivot['N_DOCUMENTI'] / tot_doc * 100).round(2)
        pivot['QUOTA_IMP (%)'] = (pivot['IMPORTO_TOT'] / tot_imp * 100).round(2)
        
        return pivot
    


    
    def assegna_voce_grafico(row):
        status = row['STATUS']
        tipo   = row['TIPOLOGIA']
        
        if tipo == 'PREVENTIVO':
            if status == 'SCADUTO':     return 'PREV. PERSI'
            if status == 'IN ATTESA':   return 'PREV. IN ATTESA'
            if status == '':            return 'PREV. VINTI'
            else:                       return 'ALTRI'
        
        if tipo == 'ORDINE':   
            if status == 'ACQUISTO DIRETTO':    return 'ACQUISTI DIRETTI'
            if status == 'ORFANO':              return 'ORD. ORFANI'
            if 'DECURTAZIONE' in status: 
                if 'ORFANA' in status:          return 'CHPR ORFANI'
                else:                           return 'CHPR'
            if status == '':                    return 'ORD. VINTI'
            else:                       return 'ALTRI'
        return 'ATTENZIONE'

    


    # 1. PULIZIA COLONNE
    df                  = df_ordini.copy()
    df['TOTALE_RIGA']   = pd.to_numeric(df['TOTALE_RIGA'], errors='coerce').fillna(0)
    df['STATUS']        = df['STATUS'].fillna('').astype(str).str.strip().str.upper()
    df['TIPOLOGIA']     = df['TIPOLOGIA'].fillna('').astype(str).str.strip().str.upper()
    df['ID_FAMIGLIA']   = df['ID_FAMIGLIA'].fillna(0)

    # 2. ASSEGNAZIONE VOCI
    df['VOCE'] = df.apply(assegna_voce_grafico, axis=1)

    # 3. ORDINI
    df_ord = df[df['TIPOLOGIA'] == 'ORDINE'].copy()

    # 4. PREVETIVI
    # Ricerca ultima revisione per i preventivi
    df_prev_all = df[df['TIPOLOGIA'] == 'PREVENTIVO'].copy()
    
    # Pulizia REV per calcolo (creiamo colonna temporanea per confrontare i numeri)
    df_prev_all['REV_NUM'] = df_prev_all['REV'].astype(str).str.replace('REV.', '', regex=False)
    df_prev_all['REV_NUM'] = pd.to_numeric(df_prev_all['REV_NUM'], errors='coerce').fillna(0)
    
    # Troviamo il numero massimo di revisione per ogni ID_FAMIGLIA
    # Usiamo transform('max') per ottenere una serie della stessa lunghezza del DF
    df_prev_all['MAX_REV'] = df_prev_all.groupby('ID_FAMIGLIA')['REV_NUM'].transform('max')
    
    # Filtriamo: teniamo solo le righe dove la REV di quella riga è uguale al massimo trovato per quella famiglia
    # (Se ID_FAMIGLIA è 0, la condizione REV_NUM == MAX_REV manterrà comunque tutte le righe originali)
    df_prev = df_prev_all[df_prev_all['REV_NUM'] == df_prev_all['MAX_REV']].copy()
    
    # Pulizia colonne di servizio prima di passare al calcolo
    df_prev = df_prev.drop(columns=['REV_NUM', 'MAX_REV'])


    # 4. TABELLE DI RIEPILOGO (Le tue funzioni invariate)
    tab_ord  = calcola_riepilogo(df_ord, is_ordine=True)
    tab_prev = calcola_riepilogo(df_prev, is_ordine=False)

    # 5. VISUALIZZAZIONE
    st.write("")
    st.write(f"#### Riepilogo")
    
    fmt = {
        'N. Doc.': '{:.0f}',
        'Quota Doc. (%)': '{:.2f}%', 
        'Importo Totale': '€ {:,.2f}', 
        'Quota (%)': '{:.2f}%'
    }

    tab1, tab2 = st.tabs(["ORDINI", "PREVENTIVI"])

    dati_tab = [(tab1, tab_ord, "ORDINI"), (tab2, tab_prev, "PREVENTIVI")]

    for tab, data, title in dati_tab:
        
        df_display = data[['VOCE', 'N_DOCUMENTI', 'QUOTA_DOC (%)', 'IMPORTO_TOT', 'QUOTA_IMP (%)']].copy()
        df_display.columns = ['VOCE', 'N. Doc.', 'Quota Doc. (%)', 'Importo Totale', 'Quota (%)']
        
        with tab:
            # 1. Visualizzazione Tabella (Centrata)
            spazio_sx, centro, spazio_dx = st.columns([0.15, 0.7, 0.15])
            with centro:
                st.table(df_display.style.format(fmt).apply(colora_righe, axis=1))
                
            # 2. Visualizzazione DUE GRAFICI AFFIANCATI
            
            g_col1, g_col2 = st.columns(2)
            
            # Grafico 1: Importi
            pull_values = [0.02] * len(data)
            with g_col1:
                # Creiamo una copia per il grafico dove l'importo è il valore assoluto
                data_plot_imp = data.copy()
                data_plot_imp['IMPORTO_ABS'] = data_plot_imp['IMPORTO_TOT'].abs()
                
                fig_imp = px.pie(data_plot_imp, values='IMPORTO_ABS', names='VOCE', 
                                    title="Distribuzione per Importo",
                                    color='VOCE', color_discrete_map=COLORI_VOCI, hole=0.3)
                
                fig_imp.update_traces(
                    texttemplate="<b>%{percent:.1%}</b><br>%{label}<br>€%{customdata[3]:,.0f}",
                    hovertemplate="<b>%{label}</b><br>" +
                                  "Importo: €%{customdata[3]:,.2f}<extra></extra>",
                    customdata=pd.concat([data[['N_DOCUMENTI', 'QUOTA_DOC (%)', 'QUOTA_IMP (%)']], data['IMPORTO_TOT']], axis=1).values,
                    textposition='outside',
                    pull=pull_values
                )
                # Toglie legenda e centra titolo
                fig_imp.update_layout(showlegend=False, title_x=0.35)
                st.plotly_chart(fig_imp, use_container_width=True)

            # Grafico 2: Numero Documenti
            with g_col2:
                fig_doc = px.pie(data, values='N_DOCUMENTI', names='VOCE', 
                                    title="Distribuzione per Numero Documenti",
                                    color='VOCE', color_discrete_map=COLORI_VOCI, hole=0.3)
                
                fig_doc.update_traces(
                    texttemplate="<b>%{percent:.1%}</b><br>%{label}<br>n. %{value:,.0f}",
                    customdata=data[['N_DOCUMENTI', 'QUOTA_DOC (%)', 'QUOTA_IMP (%)', 'IMPORTO_TOT']].values,
                    textposition='outside',
                    pull=pull_values
                )
                # Toglie legenda e centra titolo
                fig_doc.update_layout(showlegend=False, title_x=0.3)
                st.plotly_chart(fig_doc, use_container_width=True)
    