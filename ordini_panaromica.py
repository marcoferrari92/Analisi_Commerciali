import streamlit as st
import pandas as pd
import plotly.express as px

def mostra_panoramica_ordini(df_ordini, df_aperti):

    # DIZIONARIO COLORI
    COLORI_VOCI = {
        'PREV. PERSI': '#ff9999',
        'PREV. IN ATTESA': '#ffff99',
        'PREV. VINTI': '#80e680',
        'ORD. VINTI': '#80e680',
        'ORD. ORFANI': '#e9e9e9',
        'ACQUISTI DIRETTI': '#555555',
        'CHPR ORFANI': '#ff3333',
        'CHPR': '#ff3333',
        'ALTRI': '#fff200'
    }

    # Funzione che applica il colore alla riga in base alla colonna VOCE
    # Funzione aggiornata per gestire anche il colore del testo
    def colora_righe(row):
        voce = row['VOCE']
        # Definiamo il colore di sfondo
        bg_colore = COLORI_VOCI.get(voce, '#ffffff')
        
        # Definiamo il colore del testo: bianco se la voce è 'ACQUISTI DIRETTI', altrimenti nero
        txt_colore = '#ffffff' if voce == 'ACQUISTI DIRETTI' else '#000000'
        
        # Applichiamo entrambi al CSS
        return [f'background-color: {bg_colore}; color: {txt_colore}'] * len(row)

    # Funzione di aggregazione dedicata
    def calcola_riepilogo(df_sub, is_ordine):
        if is_ordine:
            df_aggr = df_sub.groupby('ID_FAMIGLIA').agg({'TOTALE_RIGA': 'sum', 'VOCE': 'first'})
        else:
            df_aggr = df_sub.groupby('ID_DOC').agg({'TOTALE_RIGA': 'sum', 'VOCE': 'first'})
        
        pivot = df_aggr.groupby('VOCE').agg(
            N_DOCUMENTI=('VOCE', 'count'),
            IMPORTO_TOT=('TOTALE_RIGA', 'sum')
        ).reset_index()
        
        tot_doc = pivot['N_DOCUMENTI'].sum()
        tot_imp = pivot['IMPORTO_TOT'].sum()
        pivot['QUOTA_DOC (%)'] = (pivot['N_DOCUMENTI'] / tot_doc * 100).round(2)
        pivot['QUOTA_IMP (%)'] = (pivot['IMPORTO_TOT'] / tot_imp * 100).round(2)
        return pivot

    def assegna_voce_grafico(row):
        status = str(row['STATUS'])
        tipo = str(row['TIPOLOGIA'])
        if tipo == 'PREVENTIVO':
            if 'SCADUTO' in status: return 'PREV. PERSI'
            if 'IN ATTESA' in status: return 'PREV. IN ATTESA'
            return 'PREV. VINTI'
        if tipo == 'ORDINE':   
            if 'ACQUISTO DIRETTO' in status: return 'ACQUISTI DIRETTI'
            if 'ORFANO' in status: return 'ORD. ORFANI'
            if 'DECURTAZIONE' in status: return 'CHPR ORFANI' if 'ORFANA' in status else 'CHPR'
            if 'ATTENZIONE' in status: return 'ALTRI'
            return 'ORD. VINTI'
        return 'ALTRI'

    # 1. PULIZIA COLONNE
    df = df_ordini.copy()
    df['TOTALE_RIGA'] = pd.to_numeric(df['TOTALE_RIGA'], errors='coerce').fillna(0)
    df['STATUS'] = df['STATUS'].fillna('').astype(str).str.strip().str.upper()
    df['TIPOLOGIA'] = df['TIPOLOGIA'].fillna('').astype(str).str.strip().str.upper()
    df['ID_FAMIGLIA'] = df['ID_FAMIGLIA'].fillna(0)

    # 2. ASSEGNAZIONE VOCI
    df['VOCE'] = df.apply(assegna_voce_grafico, axis=1)

    # 3. ORDINI
    df_ord = df[df['TIPOLOGIA'] == 'ORDINE'].copy()

    # 4. PREVENTIVI
    df_prev_all = df[df['TIPOLOGIA'] == 'PREVENTIVO'].copy()
    df_prev_all['REV_NUM'] = pd.to_numeric(df_prev_all['REV'].astype(str).str.replace('REV.', '', regex=False), errors='coerce').fillna(0)
    df_prev_all['MAX_REV'] = df_prev_all.groupby('ID_FAMIGLIA')['REV_NUM'].transform('max')
    df_prev = df_prev_all[df_prev_all['REV_NUM'] == df_prev_all['MAX_REV']].copy()
    df_prev = df_prev.drop(columns=['REV_NUM', 'MAX_REV'])

    # 5. TABELLE DI RIEPILOGO
    tab_ord = calcola_riepilogo(df_ord, is_ordine=True)
    tab_prev = calcola_riepilogo(df_prev, is_ordine=False)


   # --- 6. KPI RIASSUNTIVI (LOGICA AGGIORNATA) ---
    st.write("---")
    st.write("### 📊 Riepilogo")
    
    # 1. ORDINI (Classici)
    mask_acquisti   = (df['STATUS'] == 'ACQUISTO DIRETTO') | (df['STATUS'].str.contains('ATTENZIONE', na=False))
    df_acquisti     = df[mask_acquisti].copy()
    df_vinti        = df[(df['TIPOLOGIA'] == 'ORDINE') & (df['STATUS'] == 'ORDINE VINTO')].copy()
    vol_teorico_ord = df_prev['TOTALE_RIGA'].sum() + df_acquisti['TOTALE_RIGA'].sum()
    vol_conv_ord    = df_vinti['TOTALE_RIGA'].sum() + df_acquisti['TOTALE_RIGA'].sum()
    tasso_ord       = (vol_conv_ord / vol_teorico_ord * 100) if vol_teorico_ord > 0 else 0

    # 2. ORDINI APERTI (Logica invariata)
    vol_teorico_aperti  = df_aperti[df_aperti['TIPOLOGIA'] == 'ORDINE APERTO']['TOTALE_RIGA'].sum()
    vol_conv_aperti     = df_aperti[df_aperti['TIPOLOGIA'] == 'ORDINE']['TOTALE_RIGA'].sum()
    tasso_aperti        = (vol_conv_aperti / vol_teorico_aperti * 100) if vol_teorico_aperti > 0 else 0

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🛒 Ordini")
        st.metric("Volume Teorico", f"€ {vol_teorico_ord:,.2f}")
        st.metric("Volume Convertito", f"€ {vol_conv_ord:,.2f}", delta=f"{tasso_ord:.1f}%")

    with col2:
        st.markdown("### 📂 Ordini Aperti")
        st.metric("Volume Teorico", f"€ {vol_teorico_aperti:,.2f}")
        st.metric("Volume Convertito", f"€ {vol_conv_aperti:,.2f}", delta=f"{tasso_aperti:.1f}%")

    st.write("---")

    
    fmt = {
        'N. Doc.': '{:.0f}',
        'Quota Doc. (%)': '{:.2f}%', 
        'Importo Totale': '€ {:,.2f}', 
        'Quota (%)': '{:.2f}%'
    }

    tab1, tab2 = st.tabs(["DISTRIBUZIONE ORDINI", "CONVERSIONE PREVENTIVI"])
    dati_tab = [(tab1, tab_ord, "ORDINI"), (tab2, tab_prev, "PREVENTIVI")]

    for tab, data, title in dati_tab:
        df_display = data[['VOCE', 'N_DOCUMENTI', 'QUOTA_DOC (%)', 'IMPORTO_TOT', 'QUOTA_IMP (%)']].copy()
        df_display.columns = ['VOCE', 'N. Doc.', 'Quota Doc. (%)', 'Importo Totale', 'Quota (%)']
        with tab:
            spazio_sx, centro, spazio_dx = st.columns([0.15, 0.7, 0.15])
            with centro:
                st.table(df_display.style.format(fmt).apply(colora_righe, axis=1))
                
            g_col1, g_col2 = st.columns(2)
            pull_values = [0.02] * len(data)
            
            with g_col1:
                data_plot_imp = data.copy()
                data_plot_imp['IMPORTO_ABS'] = data_plot_imp['IMPORTO_TOT'].abs()
                fig_imp = px.pie(data_plot_imp, values='IMPORTO_ABS', names='VOCE', 
                                 title="Distribuzione per Importo", color='VOCE', 
                                 color_discrete_map=COLORI_VOCI, hole=0.3)
                fig_imp.update_traces(
                    texttemplate="<b>%{percent:.1%}</b><br>%{label}<br>€%{customdata[3]:,.0f}",
                    customdata=pd.concat([data[['N_DOCUMENTI', 'QUOTA_DOC (%)', 'QUOTA_IMP (%)']], data['IMPORTO_TOT']], axis=1).values,
                    pull=pull_values
                )
                fig_imp.update_layout(showlegend=False, title_x=0.35)
                st.plotly_chart(fig_imp, use_container_width=True)

            with g_col2:
                fig_doc = px.pie(data, values='N_DOCUMENTI', names='VOCE', 
                                 title="Distribuzione per Numero Documenti",
                                 color='VOCE', color_discrete_map=COLORI_VOCI, hole=0.3)
                fig_doc.update_traces(
                    texttemplate="<b>%{percent:.1%}</b><br>%{label}<br>n. %{value:,.0f}",
                    pull=pull_values
                )
                fig_doc.update_layout(showlegend=False, title_x=0.3)
                st.plotly_chart(fig_doc, use_container_width=True)