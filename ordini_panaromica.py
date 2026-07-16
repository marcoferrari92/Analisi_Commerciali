import streamlit as st
import pandas as pd
import plotly.express as px

def mostra_panoramica_ordini(df_pulito, data_inizio=None, data_fine=None):

    

    # DIZIONARIO COLORI
    COLORI_VOCI = {
        'PREV. PERSI': '#ff9999',
        'PREV. IN ATTESA': '#ffff99',
        'PREV. DA CONSUNTIVARE': "#800020",
        'PREV. VINTI': '#80e680',
        'ORD. VINTI': '#80e680',
        'ORD. ORFANI': '#e9e9e9',
        'ACQUISTI DIRETTI (FORM.)': '#555555',
        'CHPR ORFANI': '#800020', 
        'ACQUISTI DIRETTI (ALTRO)': '#fff200'
    }

    def colora_righe(row):
        voce = row['VOCE']
        bg_colore = COLORI_VOCI.get(voce, '#ffffff')
        txt_colore = '#ffffff' if voce in ['ACQUISTI DIRETTI (FORM.)', 'CHPR ORFANI', 'PREV. DA CONSUNTIVARE'] else '#000000'
        return [f'background-color: {bg_colore}; color: {txt_colore}'] * len(row)


    def calcola_riepilogo(df_sub):
        # Aggregazione per documento per evitare duplicati di righe
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
        status  = str(row['STATUS'])
        tipo    = str(row['TIPOLOGIA'])
        
        if tipo == 'PREVENTIVO':
            if 'SCADUTO'            in status: return 'PREV. PERSI'
            if 'IN ATTESA'          in status: return 'PREV. IN ATTESA'
            if 'VINTO'              in status: return 'PREV. VINTI'
            if 'DA CONSUNTIVARE'    in status: return 'PREV. DA CONSUNTIVARE'
            return 'PREV. IGNOTI'
        
        if tipo == 'ORDINE':   
            if 'ACQUISTO DIRETTO'       in status: return 'ACQUISTI DIRETTI (FORM.)'
            if 'ATTENZIONE'             in status: return 'ACQUISTI DIRETTI (ALTRO)'
            if 'DECURTAZIONE ORFANA'    in status: return 'CHPR ORFANI'
            if 'VINTO'                  in status: return 'ORD. VINTI'
            if 'DA CONSUNTIVARE'        in status: return 'ORD. DA CONSUNTIVARE'
            if 'DECURTAZIONE ORDINE'    in status: return 'DECURTAZIONI (COLLEGATE)'
            return 'ORD. IGNOTI'
        return 'IGNOTO'


    # 1. PULIZIA E PREPARAZIONE DATASET
    df                  = df_pulito[df_pulito['FAMIGLIA'].astype(str) == 'STANDARD'].copy()
    df['TOTALE_RIGA']   = pd.to_numeric(df['TOTALE_RIGA'], errors='coerce').fillna(0)
    df['STATUS']        = df['STATUS'].fillna('').astype(str).str.strip().str.upper()
    df['TIPOLOGIA']     = df['TIPOLOGIA'].fillna('').astype(str).str.strip().str.upper()
    df['ID_DOC']        = df['ID_DOC'].fillna(0) 
    df['VOCE']          = df.apply(assegna_voce_grafico, axis=1)
    # Escludiamo 'DECURTAZIONI (COLLEGATE)' perchè già incluse nel totale
    df = df[df['VOCE'] != 'DECURTAZIONI (COLLEGATE)'].copy()

    
    # PULIZIA REVISIONI
    # Identifichiamo i preventivi (non scaduti) e teniamo solo l'ultima rev

    df_prev_all = df[df['TIPOLOGIA'] == 'PREVENTIVO'].copy()
    df_prev_all['REV_NUM'] = pd.to_numeric(
        df_prev_all['REV'].astype(str).str.replace('REV.', '', regex=False), 
        errors='coerce'
    ).fillna(0)

    if not df_prev_all.empty:
        df_prev_all['MAX_REV'] = df_prev_all.groupby('ID_FAMIGLIA')['REV_NUM'].transform('max')
        df_prev_all = df_prev_all[df_prev_all['REV_NUM'] == df_prev_all['MAX_REV']]
    df_prev = df_prev_all.copy()

    # Dopo aver creato df_prev
    # st.write("--- DEBUG PULIZIA REVISIONI ---")
    # st.write(f"Totale originale (PREV): {df[df['TIPOLOGIA']=='PREVENTIVO']['TOTALE_RIGA'].sum():,.2f}")
    # st.write(f"Totale dopo pulizia revisioni: {df_prev['TOTALE_RIGA'].sum():,.2f}")
    # st.write(f"Differenza sparita: {df[df['TIPOLOGIA']=='PREVENTIVO']['TOTALE_RIGA'].sum() - df_prev['TOTALE_RIGA'].sum():,.2f}")

    # Gli ordini non hanno revisioni
    df_ord = df[(df['TIPOLOGIA'] == 'ORDINE') & (df['STATUS'] != 'DA CONSUNTIVARE')].copy()


    # 2. TABELLE
    tab_ord     = calcola_riepilogo(df_ord)
    tab_prev    = calcola_riepilogo(df_prev)


    # 3. KPI RIASSUNTIVI (Aggregati per ID_DOC per coerenza)
    st.write("---")
    st.write("### 📊 Riepilogo")
    

    # VOLUME TEORICO
    # Il volume teorico è il fatturato totale che dovrei chiudere 
    # (escludendo le famiglie degli ORDINI APERTI e ORDINI DA CONSUNTIVARE che tratto separatamente)
    # Vol. Teorico = somma di PREVENTIVI, ACQUISTI DIRETTI e ALTRI (tipologia particolare di acquisti diretti)
    vol_prev        = df_prev.groupby('ID_DOC')['TOTALE_RIGA'].sum().sum()
    vol_acquisti    = df_ord[df_ord['VOCE'] == 'ACQUISTI DIRETTI (FORM.)'].groupby('ID_DOC')['TOTALE_RIGA'].sum().sum()
    vol_altri       = df_ord[df_ord['VOCE'] == 'ACQUISTI DIRETTI (ALTRO)'].groupby('ID_DOC')['TOTALE_RIGA'].sum().sum()
    vol_teorico_ord = vol_prev + vol_acquisti + vol_altri

    # TASSO CONVERSIONE
    voci_da_includere   = ['ORD. VINTI', 'ACQUISTI DIRETTI (ALTRO)', 'ACQUISTI DIRETTI (FORM.)']
    vol_conv_ord        = tab_ord.loc[tab_ord['VOCE'].isin(voci_da_includere), 'IMPORTO_TOT'].sum()
    tasso_ord           = (vol_conv_ord / vol_teorico_ord * 100) if vol_teorico_ord > 0 else 0

    # ORDINI APERTI
    df_ape              = df_pulito[df_pulito['FAMIGLIA'].astype(str) == 'APERTO'].copy()
    vol_teorico_aperti  = df_ape[df_ape['TIPOLOGIA'] == 'ORDINE APERTO'].groupby('ID_DOC')['TOTALE_RIGA'].sum().sum()
    vol_conv_aperti     = df_ape[(df_ape['TIPOLOGIA'] == 'ORDINE') & (df_ape['STATUS'] != 'DA CONSUNTIVARE')].groupby('ID_DOC')['TOTALE_RIGA'].sum().sum()
    tasso_aperti        = (vol_conv_aperti / vol_teorico_aperti * 100) if vol_teorico_aperti > 0 else 0


    # VOLUME DA CONSUNTIVARE (STANDARD + APERTI)
    # Ovvero il volume degli ordini NON evasi (lista documenti)

    # 1. Volume Da Consuntivare da ORDINI STANDARD
    vol_consunt_std = df[(df['TIPOLOGIA'] == 'ORDINE') & 
                        (df['STATUS'] == 'DA CONSUNTIVARE')].groupby('ID_DOC')['TOTALE_RIGA'].sum().sum()

    # 2. Volume Da Consuntivare da ORDINI APERTI
    # Assumiamo che negli aperti, gli elementi da consuntivare siano quelli che non sono ancora 'VOCI AGGIUDICATE'
    vol_consunt_ape = df_ape[(df_ape['TIPOLOGIA'] == 'ORDINE') & 
                            (df_ape['STATUS'] == 'DA CONSUNTIVARE')].groupby('ID_DOC')['TOTALE_RIGA'].sum().sum()

    # Totale unico per la metrica generale
    tot_vol_consunt = vol_consunt_std + vol_consunt_ape

    # OUTPUT
    col1, col2, col3 = st.columns(3)
    col1.write("### ORDINI")
    col1.metric("Volume Teorico",           f"€ {vol_teorico_ord:,.2f}")
    col1.metric("Volume Convertito",        f"€ {vol_conv_ord:,.2f}",       delta=f"{tasso_ord:.1f}%")
    col2.write("### ORDINI APERTI")
    col2.metric("Volume Teorico",           f"€ {vol_teorico_aperti:,.2f}")
    col2.metric("Volume Convertito",        f"€ {vol_conv_aperti:,.2f}",    delta=f"{tasso_aperti:.1f}%")
    col3.write("### ORDINI DA CONSUNTIVARE")
    col3.metric("Volume Teorico",           f"€ {tot_vol_consunt:,.2f}")
    col3.caption(f"Ordini Standard: € {vol_consunt_std:,.2f}")
    col3.caption(f"Ordini Aperti: € {vol_consunt_ape:,.2f}")


  

    # 5. VISUALIZZAZIONE TABELLE E GRAFICI
    # Definiamo il formato corretto per le colonne già rinominate
    fmt = {
        'Num. Documeti': '{:.0f}',
        'Quota Documenti (%)': '{:.2f}%',
        'Importo Totale': '€ {:,.2f}',
        'Quota Importo (%)': '{:.2f}%'
    }
    
    # 5. VISUALIZZAZIONE TABELLE E GRAFICI
    st.write("---")
    st.write("")
    st.write("### STATISTICHE ORDINI")
    st.write("")
    tab1, tab2, tab3= st.tabs(["CONVERSIONE PREVENTIVI", "DISTRIBUZIONE ORDINI", "STATISTICHE"])
    
   
    
    for tab, data in [(tab2, tab_ord), (tab1, tab_prev)]:
        with tab:

            # Aggiunta del Popover per la spiegazione specifica
            testo_spiegazione = (
                f"""
                Qui viene mostrato come si distribuiscono gli ordini evasi tra le voci:
                * **Acquisti Diretti:** acquisti diretti dal sito-web per la formazione.
                * **Ordini Vinti:** preventivi aggiudicati e diventati ordini evasi.
                    * Gli ordini non evasi (lista doc.) non sono considerati. 
                    Verranno trattati come Preventivi Da Consuntivare nella tab Conversione Preventivi.
                * **Altri:** ordini evasi che non possiedono un preventivo. 
                
                *ATTENZIONE:* non vengono considerate le voci di un Ordine Aperto aggiudicate e diventate quindi Ordine.
                Saranno comprese nell'analisi degli Ordini Aperti come Voci Aggiudicate.
                """ 
                if tab == tab2 else 
                 f"""
                Qui viene mostrata l'analisi della conversione dei preventivi:
                * **In Attesa:** preventivi che non hanno ancora un ordine collegato.
                * **Persi:** prevetivi In Attesa per i quali è già trascorsa la finestra temporale di validità. 
                    * N.B. La finestra temporale viene ignorata se nel database viene comunque trovato un ordine collegato a quel preventivo. 
                * **Vinti:** preventivi convertiti in un ordine evaso. 
                * **Da Consuntivare:** preventivi convertiti in un ordine non ancora evaso (lista doc.).
                    
                """
            )
            
            st.write("")
            st.write("")
            st.write("")
            st.write("### Panoramica Globale")
            st.write("")
            st.write("")


            # 1. Prepariamo il DataFrame per la visualizzazione rinominando le colonne prima
            df_display = data.rename(columns={
                'N_DOCUMENTI': 'Num. Documenti', 
                'QUOTA_DOC (%)': 'Quota Documenti (%)', 
                'IMPORTO_TOT': 'Importo Totale', 
                'QUOTA_IMP (%)': 'Quota Importo (%)'
            })

            # Assicurati che le etichette qui corrispondano ESATTAMENTE ai nuovi nomi
            ordine_colonne = ['VOCE', 'Num. Documenti', 'Quota Documenti (%)', 'Importo Totale', 'Quota Importo (%)']
            
            # 2. Ora la formattazione troverà le chiavi corrette nel dizionario 'fmt'
            colonne_esistenti   = [c for c in ordine_colonne if c in df_display.columns]
            df_display          = df_display[colonne_esistenti]
            col1, col_centro, _ = st.columns([0.8, 6.4, 0.8])
            with col1:
                with st.popover(f"ℹ️ GUIDA"):
                    st.write(testo_spiegazione)
            with col_centro:
                st.table(df_display.style.format(fmt).apply(colora_righe, axis=1))
            st.write("")
            st.write("")
            
            g1, g2 = st.columns(2)
            with g1:
                # 2. Grafico Numero Documenti (con valore intero e percentuale in grassetto)
                fig = px.pie(data, values='N_DOCUMENTI', names='VOCE', 
                             title="Distribuzione per Numero Documenti", 
                             color='VOCE', color_discrete_map=COLORI_VOCI, hole=0.3)
                
                # %{value:.0f} formatta come intero
                fig.update_traces(
                    texttemplate="%{label}<br>%{value:.0f}<br><b>%{percent:.1%}</b>",
                    textposition='outside'
                )
                fig.update_layout(
                    showlegend=False,
                    title_x=0.5,
                    title_xanchor='center'
                )
                st.plotly_chart(fig, use_container_width=True)

            with g2:
                # 1. Grafico Importi (con valuta formattata e percentuale in grassetto)
                fig = px.pie(data, values='IMPORTO_TOT', names='VOCE', 
                             title="Distribuzione per Importo", 
                             color='VOCE', color_discrete_map=COLORI_VOCI, hole=0.3)
                
                fig.update_traces(
                    texttemplate="%{label}<br>€ %{value:,.2f}<br><b>%{percent:.1%}</b>",
                    textposition='outside'
                ) 
                fig.update_layout(
                    showlegend=False,
                    title_x=0.5,
                    title_xanchor='center'
                )
                st.plotly_chart(fig, use_container_width=True)


            # ========================================
            # SEZIONE: TREND SETTIMANALE (PREVENTIVI)
            # ========================================
            
            if tab == tab1:
                st.write("---")
                st.write("")
                st.write("")
                st.write("### 📈 Trend Settimanale")
                st.write("")
                st.write("")
                
                # Filtriamo dal dataframe generale tutte le voci che iniziano per 'PREV.'
                # Usiamo df perchè gli ordini da consuntivare sono da trattare come preventivi da chiudere
                df_trend = df[df['VOCE'].astype(str).str.startswith('PREV.')].copy()
                

                # Filtro temporale (nel caso non sia già stato fatto)
                df_trend['DATA_TEMP'] = pd.to_datetime(df_trend['DATA'], errors='coerce')
                df_trend = df_trend.dropna(subset=['DATA_TEMP'])
                if data_inizio is not None and data_fine is not None:
                    mask = (df_trend['DATA_TEMP'].dt.date >= data_inizio) & (df_trend['DATA_TEMP'].dt.date <= data_fine)
                    df_trend = df_trend.loc[mask]

                # Aggregazione settimanale
                df_trend['SETTIMANA'] = df_trend['DATA_TEMP'].dt.to_period('W').dt.to_timestamp()

                # Creiamo i dataset separati (emessi, vinti) per il grafico
                # Gli emessi includono tutti i prev. (vinti compresi)
                df_totale               = df_trend.copy()
                df_totale['TIPO_TREND'] = 'Preventivi Emessi'
                df_vinti                = df_trend[df_trend['VOCE'] == 'PREV. VINTI'].copy()
                df_vinti['TIPO_TREND']  = 'Preventivi Vinti'
                
                # Plot
                df_plot = pd.concat([df_totale, df_vinti])
                trend_aggr_plot = df_plot.groupby(['SETTIMANA', 'TIPO_TREND'])['TOTALE_RIGA'].sum().reset_index()

                if not trend_aggr_plot.empty:
                    fig_trend = px.area(
                        trend_aggr_plot, 
                        x='SETTIMANA', 
                        y='TOTALE_RIGA', 
                        color='TIPO_TREND',
                        #title="Confronto Settimanale: Totale Preventivato vs Vinto",
                        labels={'TOTALE_RIGA': 'Importo (€)', 'SETTIMANA': 'Settimana', 'TIPO_TREND': 'Tipo'},
                        color_discrete_map={
                            'Preventivi Emessi': "#99c5ff", 
                            'Preventivi Vinti': '#80e680'
                        }
                    )
                    
                    # Spegniamo lo stack per sovrapporre correttamente
                    fig_trend.update_traces(
                        stackgroup=None, 
                        fill='tozeroy', 
                        mode='lines+markers', 
                        marker=dict(size=10)
                    )
                    
                    # Aggiunta rette di fit
                    import numpy as np
                    color_map = {'Preventivi Emessi': "#4394ff", 'Preventivi Vinti': "#00cb00"}
                    tassi_crescita = {}
                    
                    for tipo in trend_aggr_plot['TIPO_TREND'].unique():
                        df_sub = trend_aggr_plot[trend_aggr_plot['TIPO_TREND'] == tipo].sort_values('SETTIMANA')
                        x_numeric = np.arange(len(df_sub))
                        y = df_sub['TOTALE_RIGA'].values
                        m, q = np.polyfit(x_numeric, y, 1)

                        # Tasso del trend
                        tassi_crescita[tipo] = m 
                    
                        fig_trend.add_scatter(
                            x=df_sub['SETTIMANA'], 
                            y=m * x_numeric + q, 
                            mode='lines', 
                            name=f'Trend {tipo}',
                            line=dict(dash='dash', color=color_map[tipo])
                        )

                        fig_trend.add_annotation(
                            x=df_sub['SETTIMANA'].iloc[-1], # Ultima settimana
                            y=m * x_numeric[-1] + q,        # Valore della retta in quel punto
                            text=f"Δ {m:,.0f} €/sett",
                            showarrow=False,
                            yshift=15,                      # Sposta il testo sopra la linea
                            font=dict(color=color_map[tipo], size=12, weight='bold'),
                            bgcolor="white"                 # Sfondo bianco per leggibilità
                        )
                    
                    # Mostriamo i tassi appena calcolati
                    col1, col2 = st.columns(2)
                    col1.metric("Trend Volume Prev. Emessi",    f"€ {tassi_crescita.get('Preventivi Emessi', 0):,.0f} / sett.")
                    col2.metric("Trend Volume Prev. Vinti",     f"€ {tassi_crescita.get('Preventivi Vinti', 0):,.0f} / sett.")

                    fig_trend.update_layout(height=500, hovermode="x unified")
                    st.plotly_chart(fig_trend, use_container_width=True)



                #3. Grafico Trend (Barre) + Volume (Pallini)
                st.write("### 👤 Trend per Commerciale")
                
                # 1. FILTRO BASE (TUTTO, SENZA DATE) - PER I PALLINI
                df_base = df[df['VOCE'].astype(str).str.startswith('PREV.')].copy()
                
                # 2. FILTRO TEMPORALE - PER IL GRAFICO A LINEE E TREND
                df_trend = df_base.copy()
                df_trend['DATA_TEMP'] = pd.to_datetime(df_trend['DATA'], errors='coerce')
                df_trend = df_trend.dropna(subset=['DATA_TEMP'])
                
                if data_inizio is not None and data_fine is not None:
                    mask = (df_trend['DATA_TEMP'].dt.date >= data_inizio) & (df_trend['DATA_TEMP'].dt.date <= data_fine)
                    df_trend = df_trend.loc[mask]

                # Aggregazione settimanale (solo per il trend)
                df_trend['SETTIMANA'] = df_trend['DATA_TEMP'].dt.to_period('W').dt.to_timestamp()

                # --- QUI CALCOLIAMO I PALLINI USARE IL DF_BASE (180K) ---
                df_volumi_tot = df_base.groupby(['UTENTE', 'ID_DOC'])['TOTALE_RIGA'].sum().reset_index()
                df_volumi_tot = df_volumi_tot.groupby('UTENTE')['TOTALE_RIGA'].sum().sort_values(ascending=False).reset_index()
                
                ordine_utenti = df_volumi_tot['UTENTE'].tolist()


                # B. Calcoliamo il trend per utente
                dati_trend = []
                for utente in ordine_utenti:
                    df_utente = df_trend[df_trend['UTENTE'] == utente].copy()
                    
                    for tipo in ['Preventivi Emessi', 'Preventivi Vinti']:
                        if tipo == 'Preventivi Emessi':
                            df_sub = df_utente.copy()
                        else:
                            # Qui assicurati che 'PREV. VINTI' sia il nome corretto nella colonna VOCE
                            df_sub = df_utente[df_utente['VOCE'] == 'PREV. VINTI'].copy()
                        
                        df_agg = df_sub.groupby('SETTIMANA')['TOTALE_RIGA'].sum().sort_index().reset_index()
                        
                        if len(df_agg) > 1:
                            x = np.arange(len(df_agg))
                            y = df_agg['TOTALE_RIGA'].values
                            m, q = np.polyfit(x, y, 1)
                            dati_trend.append({'UTENTE': utente, 'TIPO_TREND': tipo, 'Trend': m})
                
                df_trend_final = pd.DataFrame(dati_trend)

                # C. Creazione Grafico
                fig = px.bar(
                    df_trend_final, x='UTENTE', y='Trend', color='TIPO_TREND', barmode='group',
                    color_discrete_map={'Preventivi Emessi': "#4394ff", 'Preventivi Vinti': "#00cb00"},
                    text_auto='.0f',
                    labels={'UTENTE': 'Commerciale', 'Trend': 'Pendenza Trend (€/sett)'}
                )
                
                # I pallini con dimensione e colore variabile
                fig.add_scatter(
                    x=df_volumi_tot['UTENTE'], 
                    y=[0]*len(df_volumi_tot), 
                    mode='markers',
                    marker=dict(
                        size=df_volumi_tot['TOTALE_RIGA'], 
                        sizemode='area', 
                        sizeref=2.*max(df_volumi_tot['TOTALE_RIGA'])/(50.**2),
                        color=df_volumi_tot['TOTALE_RIGA'],
                        
                        # --- SOLUZIONE: SCALA DISCRETA ---
                        colorscale=[
                            [0.0, "#FFFFFF"], 
                            [0.25, "#9dff00"],
                            [0.50, "#FFC400"],
                            [0.75, "#FF8400"],
                            [1.0, "#FF0000"]  
                        ],
                        # ---------------------------------
                        
                        showscale=True, 
                        colorbar=dict(
                            title="Volume (€)", 
                            thickness=20, 
                            x=1.15,
                            nticks=8 # Forza solo 4 tacche sulla barra
                        ),
                        line=dict(width=1, color='black')
                    ),
                    name="Volume Totale",
                    showlegend=True
                )

                # Formattazione
                fig.update_traces(selector=dict(type='bar'), textposition='outside', cliponaxis=False)
                
                # Layout con legenda in basso (orizzontale)
                fig.update_layout(
                    height=550, 
                    template="plotly_white",
                    margin=dict(r=120), # Spazio a destra per la colorbar
                    xaxis={'categoryorder': 'array', 'categoryarray': ordine_utenti, 'title': 'Utente'},
                    yaxis={'title': 'Trend (€/sett)'},
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.2, # Posizionata sotto il grafico
                        xanchor="center",
                        x=0.5
                    )
                )
                
                fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)
                
                st.plotly_chart(fig, use_container_width=True)

        

           
                
            

    # with tab3:
        

    #     # Aggiunta del Popover per la spiegazione specifica
    #     testo_spiegazione = (
    #         f"""
    #         Qui viene mostrato lo stato di avanzamento degli Ordini Aperti secondo questi tre stadi:
    #         * **Preventivo:** l'ordine è stato preventivato.
    #         * **Ordine Aperto:** il preventivo è stato convertito in Ordine Aperto. 
    #         * **Voce Aggiudicata:** una delle voci del preventivo è stata chiusa e trasformata in un Ordine evaso (storico doc.).
    #         """
    #     )
        
    #     st.write("")
    #     with st.popover(f"ℹ️ GUIDA"):
    #         st.write(testo_spiegazione)
    #     st.write("")

    #     col_f1, col_f2 = st.columns([1, 1])
        
    #     with col_f1:
    #         fig_funnel = px.funnel(df_funnel, x='Importo', y='Fase', 
    #                                title="Flusso conversioni degli Ordini Aperti",
    #                                color_discrete_sequence=['#ffcc00', '#66b3ff', '#99ff99'])
    #         # Formattazione per mostrare l'euro nel funnel
    #         fig_funnel.update_traces(texttemplate="€ %{x:,.0f}")
    #         st.plotly_chart(fig_funnel, use_container_width=True)



    with tab3:
        # --- DEFINIZIONE ETICHETTE (Personalizza qui) ---
        NOMI_COLONNE_PERF = {
            'UTENTE': 'Commerciale',
            'TOTALE_VENDUTO': 'Volume Totale (€)',
            'NUM_ORDINI': 'N. Ordini',
            'TICKET_MEDIO': 'Valore Medio Ordine (€)'
        }
        
        NOMI_COLONNE_EFF = {
            'UTENTE': 'Commerciale',
            'TOT_PREV': 'Preventivi Emessi',
            'TOT_VINTI': 'Ordini Vinti',
            'TASSO_CONV (%)': 'Tasso di Conversione (%)'
        }

        # Recupero palette colori
        utenti_unici = df_pulito['UTENTE'].dropna().unique()
        palette_base = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
        COLORI_UTENTI = {utente: palette_base[i % len(palette_base)] for i, utente in enumerate(utenti_unici)}

        st.write("")
        st.write("### Quote Commerciali")
        
        df_comm = df_ord.copy()
        
        if not df_comm.empty:
            df_statistiche = calcola_performance_commerciali(df_comm)
            # Rinominiamo le colonne per la visualizzazione
            df_stat_display = df_statistiche.rename(columns=NOMI_COLONNE_PERF)
            
            # --- TABELLA INTERATTIVA ---
            st.dataframe(
                df_stat_display.style.format({
                    'Volume Totale (€)': '€ {:,.2f}',
                    'Valore Medio Ordine (€)': '€ {:,.2f}',
                    'N. Ordini': '{:.0f}'
                }),
                use_container_width=True
            )
            
            # 2. GRAFICI PERFORMANCE
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                media_venduto = df_statistiche['TOTALE_VENDUTO'].mean()
                fig_bar = px.bar(df_statistiche, x='UTENTE', y='TOTALE_VENDUTO',
                                title="Volume Venduto per Commerciale",
                                labels={'UTENTE': 'Commerciale', 'TOTALE_VENDUTO': 'Volume (€)'}, # Etichette assi
                                color='UTENTE', 
                                color_discrete_map=COLORI_UTENTI,
                                text_auto='.2s')
                fig_bar.add_hline(y=media_venduto, line_dash="dash", line_color="red", 
                                annotation_text=f"Media: € {media_venduto:,.0f}",
                                annotation_position="top right")
                st.plotly_chart(fig_bar, use_container_width=True)
                
            with col_g2:
                fig_pie = px.pie(df_statistiche, values='TOTALE_VENDUTO', names='UTENTE',
                                title="Quota di Mercato per Commerciale",
                                color='UTENTE', 
                                color_discrete_map=COLORI_UTENTI)
                st.plotly_chart(fig_pie, use_container_width=True)





        # --- CALCOLO EFFICIENZA ---
        df_prev_count = df_prev.groupby('UTENTE')['ID_DOC'].nunique().reset_index()
        df_prev_count.columns = ['UTENTE', 'TOT_PREV']

        df_vinti_count = df_ord[df_ord['VOCE'] == 'ORD. VINTI'].groupby('UTENTE')['ID_DOC'].nunique().reset_index()
        df_vinti_count.columns = ['UTENTE', 'TOT_VINTI']

        df_efficienza = pd.merge(df_prev_count, df_vinti_count, on='UTENTE', how='left').fillna(0)
        df_efficienza['TASSO_CONV (%)'] = (df_efficienza['TOT_VINTI'] / df_efficienza['TOT_PREV'] * 100).round(2)
        df_efficienza = df_efficienza.sort_values(by='TASSO_CONV (%)', ascending=False)

        # --- VISUALIZZAZIONE EFFICIENZA ---
        st.write("### Efficienza Commerciali")
        
        # Rinominiamo le colonne per la visualizzazione
        df_eff_display = df_efficienza.rename(columns=NOMI_COLONNE_EFF)

        # Tabella aggiornata
        st.dataframe(
            df_eff_display.style.format({
                'Ordini Vinti': '{:.0f}', 
                'Preventivi Emessi': '{:.0f}',
                'Tasso di Conversione (%)': '{:.2f}%'
            }).background_gradient(
                subset=['Tasso di Conversione (%)'],  # <-- Usa il nome della colonna NUOVO
                cmap='Greens'
            ),
            use_container_width=True
        )

        fig_conv = px.bar(df_efficienza, x='UTENTE', y='TASSO_CONV (%)',
                        title="Tasso Conversione Preventivi (%)",
                        labels={'UTENTE': 'Commerciale', 'TASSO_CONV (%)': 'Tasso Conv. (%)'}, # Etichette assi
                        color='UTENTE', 
                        color_discrete_map=COLORI_UTENTI,
                        text_auto='.2f')
        st.plotly_chart(fig_conv, use_container_width=True)

        # --- GRAFICO A BOLLE: VOLUME, NUMERO, EFFICIENZA ---
        st.write("### 📊 Analisi Combinata (Volume, Numero, Efficienza)")

        # Creiamo un unico dataframe unificato per il grafico
        df_combinato = pd.merge(df_statistiche, df_efficienza, on='UTENTE')
        
        fig_bubble = px.scatter(
            df_combinato, 
            x='NUM_ORDINI', 
            y='TASSO_CONV (%)', 
            size='TOTALE_VENDUTO', 
            color='UTENTE',
            color_discrete_map=COLORI_UTENTI,
            hover_name='UTENTE',
            size_max=60, # Dimensione massima bolle
            title="Analisi: Efficienza (Y) vs Volume Ordini (X) vs Fatturato (Dimensione)",
            labels={'NUM_ORDINI': 'N. Ordini', 'TASSO_CONV (%)': 'Tasso Conversione (%)'}
        )
        
        # Aggiungiamo linee di riferimento per dividere i quadranti
        fig_bubble.add_hline(y=df_combinato['TASSO_CONV (%)'].mean(), line_dash="dot", annotation_text="Media Conv.")
        fig_bubble.add_vline(x=df_combinato['NUM_ORDINI'].mean(), line_dash="dot", annotation_text="Media Ordini")
        
        st.plotly_chart(fig_bubble, use_container_width=True)




def calcola_performance_commerciali(df_sub):
    # Aggreghiamo per commerciale: totale importo e numero di ordini
    df_perf = df_sub.groupby('UTENTE').agg(
        TOTALE_VENDUTO=('TOTALE_RIGA', 'sum'),
        NUM_ORDINI=('ID_DOC', 'nunique')
    ).reset_index().sort_values(by='TOTALE_VENDUTO', ascending=False)
    
    # Calcolo ticket medio
    df_perf['TICKET_MEDIO'] = df_perf['TOTALE_VENDUTO'] / df_perf['NUM_ORDINI']
    return df_perf




    