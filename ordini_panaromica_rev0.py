import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import io

# ==============================================================================
# CONFIGURAZIONI E PALETTE COLORI COSTANTI
# ==============================================================================
PALETTE_FLUSSI = {
    "STANDARD": {
        "STD - PREVENTIVO": "#A2D2FF",
        "STD - ORDINE": "#4E944F",
        "STD - ORFANO": "#D3D3D3"
    },
    "APERTO": {
        "APE - PREVENTIVO": "#FFC0D9", 
        "APE - ORDINE": "#B4E197",       
        "APE - VOCE AGGIUDICATA": "#80B341", 
        "APE - ORDINE CONCLUSO": "#2C5E3B",
        "APE - ORFANO": "#9E9E9E"
    },
    "ECCEZIONI": {
        "ERRORE": "#FF6B6B"
    }
}

# ==============================================================================
# FUNZIONI DI SUPPORTO GRAFICO (RIUTILIZZABILI)
# ==============================================================================
def render_sezione_flusso(df_filtrato, stadi_ordine, palette_corrente, prefisso_chiave):
    """
    Sotto-interfaccia modulare: genera Torte, Tabelle Metriche e Distribuzione.
    """
    if df_filtrato.empty:
        st.info("Nessun dato presente per questo flusso con i filtri attuali.")
        return

    # Evitiamo di duplicare i calcoli economici aggregando sui documenti univoci
    df_doc_univoci = df_filtrato.drop_duplicates(subset=['ID DOCUMENTO'])

    conteggio_qty = df_doc_univoci['TIPOLOGIA DOC.'].value_counts().reset_index()
    conteggio_qty.columns = ['TIPOLOGIA DOC.', 'Conteggio'] 
    conteggio_vol = df_doc_univoci.groupby('TIPOLOGIA DOC.')['TOTALE'].sum().reset_index()

    col_sinistra, col_destra = st.columns(2)
    with col_sinistra:
        fig_qty = px.pie(conteggio_qty, values='Conteggio', names='TIPOLOGIA DOC.', title="N. Documenti Distribuiti",
                         hole=0.4, color='TIPOLOGIA DOC.', color_discrete_map=palette_corrente, category_orders={'TIPOLOGIA DOC.': stadi_ordine})
        fig_qty.update_traces(textinfo='percent+value+label', texttemplate='%{label}<br>%{percent}<br>N. %{value}', pull=[0.05] * len(conteggio_qty), marker=dict(line=dict(color='#FFFFFF', width=2)), sort=False)
        fig_qty.update_layout(height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5), margin=dict(t=100, b=20, l=20, r=20), title_x=0.35)
        st.plotly_chart(fig_qty, use_container_width=True, key=f"pie_qty_{prefisso_chiave}")
        
    with col_destra:
        fig_vol = px.pie(conteggio_vol, values='TOTALE', names='TIPOLOGIA DOC.', title="Valore Economico Complessivo",
                         hole=0.4, color='TIPOLOGIA DOC.', color_discrete_map=palette_corrente, category_orders={'TIPOLOGIA DOC.': stadi_ordine})
        fig_vol.update_traces(textinfo='percent+value+label', texttemplate='%{label}<br>%{percent}<br>€%{value:,.2f}', pull=[0.05] * len(conteggio_vol), marker=dict(line=dict(color='#FFFFFF', width=2)), sort=False)
        fig_vol.update_layout(height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5), margin=dict(t=100, b=20, l=20, r=20), title_x=0.35)
        st.plotly_chart(fig_vol, use_container_width=True, key=f"pie_vol_{prefisso_chiave}")
    
    mediane = df_doc_univoci.groupby('TIPOLOGIA DOC.')['TOTALE'].median().reset_index().rename(columns={'TOTALE': 'Mediana (€)'})
    df_riepilogo = pd.merge(conteggio_qty, conteggio_vol, on='TIPOLOGIA DOC.')
    df_riepilogo = pd.merge(df_riepilogo, mediane, on='TIPOLOGIA DOC.')
    
    tot_qty = df_riepilogo['Conteggio'].sum()
    tot_vol = df_riepilogo['TOTALE'].sum()
    df_riepilogo['% Qty'] = (df_riepilogo['Conteggio'] / tot_qty * 100).round(1).astype(str) + '%'
    df_riepilogo['% Vol'] = (df_riepilogo['TOTALE'] / tot_vol * 100).round(1).astype(str) + '%'
    df_riepilogo['Media (€)'] = (df_riepilogo['TOTALE'] / df_riepilogo['Conteggio'])
    
    stadi_effettivi = [s for s in stadi_ordine if s in df_riepilogo['TIPOLOGIA DOC.'].values]
    df_riepilogo['TIPOLOGIA DOC.'] = pd.Categorical(df_riepilogo['TIPOLOGIA DOC.'], categories=stadi_effettivi, ordered=True)
    df_riepilogo = df_riepilogo.sort_values('TIPOLOGIA DOC.')
    
    st.write("")
    st.dataframe(
        df_riepilogo[['TIPOLOGIA DOC.', 'Conteggio', '% Qty', 'TOTALE', '% Vol', 'Media (€)', 'Mediana (€)']].style.format({'TOTALE': '€ {:,.2f}', 'Media (€)': '€ {:,.2f}', 'Mediana (€)': '€ {:,.2f}'}),
        use_container_width=True, hide_index=True
    )
    
    st.divider()
    st.write("#### Analisi della Distribuzione delle Fasi")
    
    df_plot = df_doc_univoci.copy()
    df_plot['DATA_Str'] = pd.to_datetime(df_plot['DATA']).dt.strftime('%d/%m/%Y') if 'DATA' in df_plot.columns else "N.D."
    
    bin_key = f"bin_size_{prefisso_chiave}"
    if bin_key not in st.session_state:
        st.session_state[bin_key] = 1000
        
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.5])
    
    for stadio in stadi_effettivi:
        df_stadio = df_plot[df_plot['TIPOLOGIA DOC.'].astype(str) == stadio]
        if df_stadio.empty: continue
        vals = df_stadio['TOTALE']
        
        fig.add_trace(go.Histogram(x=vals, name=stadio, marker_color=palette_corrente.get(stadio, "#CCCCCC"), opacity=0.6, xbins=dict(size=st.session_state[bin_key]), marker_line=dict(width=1, color='white'), legendgroup=stadio), row=2, col=1)
        fig.add_trace(go.Box(x=vals, name=stadio, marker_color=palette_corrente.get(stadio, "#CCCCCC"), boxpoints='all', jitter=0.5, pointpos=0, legendgroup=stadio, showlegend=False, orientation='h', customdata=df_stadio[['DATA_Str', 'ID DOCUMENTO', 'CLIENTE', 'TITOLO']] if 'CLIENTE' in df_stadio.columns else None, hovertemplate="<b>TOTALE:</b> €%{x:,.2f}<br><b>ID:</b> %{customdata[1]}<br><extra></extra>"), row=1, col=1)
        
    fig.update_layout(height=650, barmode='overlay', margin=dict(t=50, b=50, l=50, r=50), legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"), xaxis=dict(type='linear', gridcolor='lightgray'))
    st.plotly_chart(fig, use_container_width=True, key=f"dist_plot_{prefisso_chiave}")
    
    col1, col2, col3 = st.columns(3)
    with col2:
        st.slider("Fascia istogramma (€)", min_value=100, max_value=10000, value=1000, step=100, format="%d €", key=bin_key)


# ==============================================================================
# FUNZIONE PRINCIPALE ORCHESTRATRICE CHIAMATA DALL'APP
# ==============================================================================
def mostra_panoramica_ordini(df_orders_pulito):
    """
    Ripristina l'input corretto df_orders_pulito ed effettua una riclassificazione 
    blindata e case-insensitive basata sulle 3 voci native del JSON.
    """
    st.title("📊 Monitoraggio Avanzato Pipeline Vendite")

    # Standardizzazione preventiva di sicurezza sulle colonne per evitare KeyError
    df_working = df_orders_pulito.copy()
    if 'ID DOCUMENTO' in df_working.columns:
        df_working['ID DOCUMENTO'] = df_working['ID DOCUMENTO'].astype(str).str.strip()
    if 'ID DOCUMENTO PADRE' in df_working.columns:
        df_working['ID DOCUMENTO PADRE'] = df_working['ID DOCUMENTO PADRE'].fillna('').astype(str).str.strip()
    if 'TIPOLOGIA DOC.' in df_working.columns:
        df_working['TIPOLOGIA DOC.'] = df_working['TIPOLOGIA DOC.'].astype(str).str.upper().str.strip()
    else:
        # Fallback se la colonna ha un nome leggermente diverso
        for col in df_working.columns:
            if 'TIPO' in col.upper():
                df_working['TIPOLOGIA DOC.'] = df_working[col].astype(str).str.upper().str.strip()

    if 'EVASO' in df_working.columns:
        df_working['EVASO'] = df_working['EVASO'].astype(str).str.upper().str.strip()
    else:
        df_working['EVASO'] = 'NO'

    if 'REVISIONATO' in df_working.columns:
        df_working['REVISIONATO'] = df_working['REVISIONATO'].astype(str).str.upper().str.strip()
    else:
        df_working['REVISIONATO'] = 'NO'

    # Conserviamo una copia esatta del tipo documento iniziale del JSON
    df_working['TIPO_JSON_ORIGINALE'] = df_working['TIPOLOGIA DOC.']

    # Costruzione dei set relazionali di monte prima delle ridenominazioni
    id_preventivi_globali = set(df_working[df_working['TIPO_JSON_ORIGINALE'] == 'PREVENTIVO']['ID DOCUMENTO'])
    id_ordini_aperti_globali = set(df_working[df_working['TIPO_JSON_ORIGINALE'] == 'ORDINE APERTO']['ID DOCUMENTO'])
    padri_di_ordini_apt = set(df_working[df_working['TIPO_JSON_ORIGINALE'] == 'ORDINE APERTO']['ID DOCUMENTO PADRE'])

    # --------------------------------------------------------------------------
    # ALGORITMO DI RIDISTRIBUZIONE ORIENTATO AI REALI INPUT DEL JSON
    # --------------------------------------------------------------------------
    def ridistribuisci_etichette_e_info(row):
        tipo_json = row['TIPO_JSON_ORIGINALE']
        id_doc = row['ID DOCUMENTO']
        padre = row['ID DOCUMENTO PADRE']
        
        # --- PREVENTIVO ---
        if tipo_json == 'PREVENTIVO':
            if id_doc in padri_di_ordini_apt:
                return 'APE - PREVENTIVO', 'OK - Preventivo associato a un Ordine Aperto quadro'
            else:
                return 'STD - PREVENTIVO', 'OK - Preventivo associato a un Ordine Standard'
                
        # --- ORDINE ---
        elif tipo_json == 'ORDINE':
            if padre == '':
                return 'ERRORE', 'Anomalia: Il documento di tipo Ordine non ha un ID Padre valorizzato (campo vuoto)'
            if padre in id_ordini_aperti_globali:
                return 'APE - VOCE AGGIUDICATA', 'OK - Spedizione/Erosione agganciata correttamente al contratto'
            elif padre in id_preventivi_globali:
                return 'STD - ORDINE', 'OK - Ordine standard convertito da preventivo'
            else:
                return 'STD - ORFANO', 'OK - Ordine standard il cui preventivo è antecedente al file caricato'

        # --- ORDINE APERTO ---
        elif tipo_json == 'ORDINE APERTO':
            if padre == '':
                return 'ERRORE', 'Anomalia: L\'Ordine Aperto non ha un ID Padre valorizzato (campo vuoto)'
            if padre in id_preventivi_globali:
                return 'APE - ORDINE', 'OK - Contratto Quadro convertito da Preventivo Aperto'
            else:
                return 'APE - ORFANO', 'OK - Ordine aperto il cui preventivo di origine è antecedente al file'

        return 'ERRORE', f'Anomalia: La stringa originale \'{tipo_json}\' non rientra nei tre stadi base (PREVENTIVO, ORDINE, ORDINE APERTO)'

    # Eseguiamo la mappatura delle label e popoliamo la colonna INFO
    elaborazione = df_working.apply(ridistribuisci_etichette_e_info, axis=1)
    df_working['TIPOLOGIA DOC.'] = [e[0] for e in elaborazione]
    df_working['INFO'] = [e[1] for e in elaborazione]

    # --------------------------------------------------------------------------
    # GENERAZIONE ALBERO E ASSEGNAZIONE ID FLUSSO SEQUENZIALE NUMERICO
    # --------------------------------------------------------------------------
    def trova_radice_flusso(row):
        padre = row['ID DOCUMENTO PADRE']
        id_doc = row['ID DOCUMENTO']
        if padre == '' or row['TIPOLOGIA DOC.'] in ['STD - ORFANO', 'APE - ORFANO', 'ERRORE']:
            return id_doc
        if row['TIPOLOGIA DOC.'] == 'APE - VOCE AGGIUDICATA':
            record_padre = df_working[df_working['ID DOCUMENTO'] == padre]
            if not record_padre.empty:
                padre_del_padre = record_padre.iloc[0]['ID DOCUMENTO PADRE']
                if padre_del_padre != '':
                    return padre_del_padre
        return padre

    df_working['ID_RADICE_FLUSSO'] = df_working.apply(trova_radice_flusso, axis=1)
    
    radici_univoche = df_working.sort_values('DATA')['ID_RADICE_FLUSSO'].unique()
    mappa_id_sequenziale_numerico = {id_radice: int(i + 1) for i, id_radice in enumerate(radici_univoche)}
    df_working['ID FLUSSO'] = df_working['ID_RADICE_FLUSSO'].map(mappa_id_sequenziale_numerico)

    # Ordinamento cronologico
    if 'DATA' in df_working.columns:
        df_working['DATA_DT'] = pd.to_datetime(df_working['DATA'], errors='coerce')
        df_working = df_working.sort_values(by=['ID FLUSSO', 'DATA_DT']).drop(columns=['DATA_DT'])

    # CONTROLLO INTEGRATO DELLE CHIUSURE DEI CONTRATTI (APE - ORDINE CONCLUSO)
    df_solo_voci = df_working[df_working['TIPOLOGIA DOC.'] == 'APE - VOCE AGGIUDICATA']
    id_padri_conclusi = []
    if not df_solo_voci.empty:
        stato_evasione_padri = df_solo_voci.groupby('ID DOCUMENTO PADRE')['EVASO'].apply(lambda x: (x == 'SI').all())
        id_padri_conclusi = stato_evasione_padri[stato_evasione_padri == True].index.tolist()
        id_padri_conclusi = [str(x) for x in id_padri_conclusi if str(x) != '']

    # --------------------------------------------------------------------------
    # 📜 TABELLA STORICA SEQUENZIALE REALE (REVISIONATO DOPO ID PADRE)
    # --------------------------------------------------------------------------
    with st.expander("📜 Ricostruzione Storica dei Flussi (ID Sequenziale Numerico)", expanded=True):
        st.markdown("""
        I documenti sono stati aggregati in base all'**ID FLUSSO** numerico progressivo. 
        La colonna nativa **REVISIONATO** si trova esattamente a valle di **ID DOCUMENTO PADRE**.
        """)
        
        # Lista delle colonne pulita e ordinata senza alcun duplicato o contatore artificiale
        colonne_storia_finali = [
            'ID FLUSSO', 
            'ID DOCUMENTO', 
            'ID DOCUMENTO PADRE', 
            'REVISIONATO',  # <--- Posizionato esattamente qui
            'TIPO_JSON_ORIGINALE', 
            'TIPOLOGIA DOC.', 
            'DATA', 
            'CLIENTE', 
            'EVASO', 
            'TOTALE'
        ]
        
        # Filtro preventivo di sicurezza per estrarre solo le colonne effettivamente disponibili nel DataFrame
        colonne_storia_presenti = [c for c in colonne_storia_finali if c in df_working.columns]
        df_tabella_storia = df_working[colonne_storia_presenti]
        
        st.dataframe(
            df_tabella_storia.style.format({'ID FLUSSO': '{:d}', 'TOTALE': '€ {:,.2f}'}),
            use_container_width=True, hide_index=True
        )
        
        def genera_excel_storia(dataframe):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                dataframe.to_excel(writer, index=False, sheet_name='Cronologia_Flussi')
            return output.getvalue()
            
        dati_excel_storia = genera_excel_storia(df_tabella_storia)
        st.download_button(
            label="📥 Esporta Tabella Storica Sequenziale in Excel (.xlsx)", 
            data=dati_excel_storia, 
            file_name="cronologia_sequenziale_flussi.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # --------------------------------------------------------------------------
    # TABELLA DI CONTROLLO GENERALE
    # --------------------------------------------------------------------------
    with st.expander("🔍 Tabella di Controllo Generale (Filtri e Colonna INFO integrati)", expanded=False):
        df_ispezione = df_working.copy()
        df_ispezione['ID FLUSSO (PADRE)'] = df_ispezione['ID DOCUMENTO PADRE'].apply(lambda x: x if x != '' else 'Documento Radice')
        df_ispezione['STATO CONTRATTO'] = df_ispezione.apply(
            lambda r: 'ORDINE APERTO ORFANO (Padre antecedente)' if r['TIPOLOGIA DOC.'] == 'APE - ORFANO' 
            else ('AGGREGATO NELL\'ORDINE CONCLUSO' if r['ID DOCUMENTO PADRE'] in id_padri_conclusi else 'In Corso / Attivo'), axis=1
        )
        
        colonne_visualizzate = ['ID DOCUMENTO', 'ID FLUSSO (PADRE)', 'TIPOLOGIA DOC.', 'DATA', 'CLIENTE', 'REVISIONATO', 'EVASO', 'INFO', 'TOTALE']
        colonne_presenti_ispezione = [c for c in colonne_visualizzate if c in df_ispezione.columns]
        df_export_final = df_ispezione[colonne_presenti_ispezione]
        
        st.dataframe(df_export_final.style.format({'TOTALE': '€ {:,.2f}'}), use_container_width=True, hide_index=True)
        
        def genera_excel_standard(dataframe):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                dataframe.to_excel(writer, index=False, sheet_name='Ispezione_Flussi')
            return output.getvalue()
        
        dati_excel = genera_excel_standard(df_export_final)
        st.write("")
        st.download_button(label="📥 Esporta Tabella di Controllo Generale in Excel (.xlsx)", data=dati_excel, file_name="esportazione_controllo_generale.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.divider()

    palette_unificata = {**PALETTE_FLUSSI["STANDARD"], **PALETTE_FLUSSI["APERTO"], **PALETTE_FLUSSI["ECCEZIONI"]}

    # Generazione dei Tab dell'interfaccia grafici
    tab_standard, tab_aperti, tab_errori = st.tabs(["🛒 Flusso Ordini Standard", "🔄 Flusso Ordini Aperti e Contratti", "⚠️ Anomalie e Errori"])

    # --- TAB 1: FLUSSO ORDINI STANDARD ---
    with tab_standard:
        st.subheader("Pipeline Standard: Preventivi ➔ Ordini")
        stadi_standard = ["STD - PREVENTIVO", "STD - ORDINE", "STD - ORFANO"]
        df_standard = df_working[df_working['TIPOLOGIA DOC.'].isin(stadi_standard)]
        render_sezione_flusso(df_standard, stadi_standard, palette_unificata, "std")

    # --- TAB 2: FLUSSO ORDINI APERTI / CONTRATTI ---
    with tab_aperti:
        st.subheader("Pipeline Contratti: Ordini Aperti in Corso ed Erosioni")
        stadi_ricerca = ["APE - PREVENTIVO", "APE - ORDINE", "APE - VOCE AGGIUDICATA", "APE - ORFANO"]
        df_aperti_raw = df_working[df_working['TIPOLOGIA DOC.'].isin(stadi_ricerca)].copy()
        
        if not df_aperti_raw.empty:
            lista_blocchi_df = []
            df_in_corso = df_aperti_raw[(~df_aperti_raw['ID DOCUMENTO PADRE'].isin(id_padri_conclusi)) & (~df_aperti_raw['ID DOCUMENTO'].isin(id_padri_conclusi))]
            lista_blocchi_df.append(df_in_corso)
            
            df_famiglia_conclusa = df_aperti_raw[(df_aperti_raw['ID DOCUMENTO PADRE'].isin(id_padri_conclusi)) | (df_aperti_raw['ID DOCUMENTO'].isin(id_padri_conclusi))]
            if not df_famiglia_conclusa.empty:
                df_struttura_padre = df_famiglia_conclusa[df_famiglia_conclusa['TIPOLOGIA DOC.'].isin(["APE - PREVENTIVO", "APE - ORDINE"])]
                lista_blocchi_df.append(df_struttura_padre)
                
                df_figli_da_accorpare = df_famiglia_conclusa[df_famiglia_conclusa['TIPOLOGIA DOC.'] == 'APE - VOCE AGGIUDICATA']
                if not df_figli_da_accorpare.empty:
                    df_accorpato = df_figli_da_accorpare.groupby(['ID DOCUMENTO PADRE', 'CLIENTE'], as_index=False).agg({'TOTALE': 'sum', 'ID DOCUMENTO': 'first'})
                    df_accorpato['TIPOLOGIA DOC.'] = "APE - ORDINE CONCLUSO"
                    lista_blocchi_df.append(df_accorpato)
                    
            df_aperti_final = pd.concat(lista_blocchi_df, ignore_index=True)
        else:
            df_aperti_final = df_aperti_raw

        stadi_aperti_cronologici = ["APE - PREVENTIVO", "APE - ORDINE", "APE - VOCE AGGIUDICATA", "APE - ORDINE CONCLUSO", "APE - ORFANO"]
        render_sezione_flusso(df_aperti_final, stadi_aperti_cronologici, palette_unificata, "apt")

    # --- TAB 3: ERRORI E ANOMALIE STRUTTURALI ---
    with tab_errori:
        st.subheader("⚠️ Analisi dei Record non Conformi (ERRORE)")
        df_errori_focussati = df_working[df_working['TIPOLOGIA DOC.'].isin(['ERRORE'])]
        
        if df_errori_focussati.empty:
            st.success("🎉 Eccellente! Nessun errore strutturale rilevato (tutti i padri e le relazioni sono coerenti).")
        else:
            c1, c2 = st.columns(2)
            c1.metric("Numero Documenti in Errore", f"{len(df_errori_focussati.drop_duplicates(subset=['ID DOCUMENTO']))} u.b.")
            c2.metric("Volume Economico Interessato", f"€ {df_errori_focussati.drop_duplicates(subset=['ID DOCUMENTO'])['TOTALE'].sum():,.2f}")
            
            st.write("#### Elenco Errori Bloccanti con Spiegazione (`INFO`)")
            st.dataframe(df_errori_focussati[['ID DOCUMENTO', 'ID DOCUMENTO PADRE', 'CLIENTE', 'TOTALE', 'INFO']].drop_duplicates(subset=['ID DOCUMENTO']).style.format({'TOTALE': '€ {:,.2f}'}), use_container_width=True, hide_index=True)