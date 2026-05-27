import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import re
import json
import numpy as np

st.set_page_config(layout="wide")

from eventi_panoramica import distribuzione_eventi
from eventi_performance_team import analisi_performance_utenti
from eventi_aziende import coinvolgimento_aziende

@st.cache_data
def carica_dati_eventi(file):
    try:
        # 1. Lettura file con gestione separatore
        df = pd.read_csv(file, sep=';', encoding='utf-8-sig')
        if df.shape[1] <= 1:
            file.seek(0)
            df = pd.read_csv(file, sep=',', encoding='utf-8-sig')

        # 2. Pulizia preliminare spazi e caratteri invisibili (BOM)
        df.columns = df.columns.str.strip().str.replace('ï»¿', '', regex=False)
        
        # Rinominiamo 'Data Evento' in 'DATA' per le tue funzioni di filtraggio
        if 'Data Evento' in df.columns:
            df = df.rename(columns={'Data Evento': 'DATA'})
        
        # Trasformiamo TUTTI i nomi delle colonne in maiuscolo
        df.columns = [c.upper() for c in df.columns]

        # 4. Controllo colonne obbligatorie (Tutte tranne CAMPAGNA)
        # Queste sono le colonne del tuo file eventi.csv dopo la trasformazione in maiuscolo
        colonne_necessarie = [
            'TIPO ANAGRAFICA', 'ID CLIENTI', 'RAGIONE SOCIALE', 
            'DATA', 'ORA EVENTO', 'TIPO EVENTO', 'UTENTE', 'NOTE'
        ]
        
        mancanti = [c for c in colonne_necessarie if c not in df.columns]
        
        if mancanti:
            st.error(f"⚠️ Errore: Il file non contiene tutte le colonne necessarie.")
            st.info(f"Colonne mancanti: {mancanti}")
            return None

        # 5. Gestione specifica della DATA
        df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce')
        righe_nulle = df['DATA'].isna().sum()
        df = df.dropna(subset=['DATA'])
        
        if righe_nulle > 0:
            st.warning(f"⚠️ Rimosse {righe_nulle} righe con DATA non valida o vuota.")

        # 6. Pulizia testi (Maiuscolo e rimozione spazi)
        # Rendiamo tutto maiuscolo per evitare discrepanze nei filtri (es. 'telefonata' vs 'TELEFONATA')
        colonne_testo = ['UTENTE', 'TIPO EVENTO', 'TIPO ANAGRAFICA', 'RAGIONE SOCIALE']
        for col in colonne_testo:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()

        return df

    except Exception as e:
        st.error(f"❌ Errore critico nel caricamento: {e}")
        return None
        

@st.cache_data
def carica_dati_ordini(file):
    
    try:
        # 1. Lettura file
        df = pd.read_csv(file, sep=';', encoding='utf-8-sig')
        if df.shape[1] <= 1:
            file.seek(0)
            df = pd.read_csv(file, sep=',', encoding='utf-8-sig')

        # 2. Pulizia preliminare spazi e caratteri invisibili
        df.columns = df.columns.str.strip().str.replace('ï»¿', '', regex=False)

        # 3. Controllo colonne obbligatorie
        colonne_necessarie = ['DATA', 'ID DOCUMENTO', 'CODICE GESTIONALE UTENTE', 'CLIENTE', 'TIPOLOGIA DOC.', 'CODICE ARTICOLO', 'PREZZO', 'QT']
        mancanti = [c for c in colonne_necessarie if c not in df.columns]
        if mancanti:
            st.error(f"Mancano colonne fondamentali: {mancanti}")
            st.info(f"Colonne rilevate nel file: {list(df.columns)}")
            return None

        # 4. Gestione specifica della DATA
        df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce')
        righe_nulle = df['DATA'].isna().sum()
        df = df.dropna(subset=['DATA'])
        
        if righe_nulle > 0:
            st.warning(f"⚠️ Rimosse {righe_nulle} righe con DATA non valida.")

        return df

    except Exception as e:
        st.error(f"Errore critico caricamento: {e}")
        return None


def DATA_range(df):
    
    date = df['DATA'].dropna()
    
    if not date.empty:
        d_min, d_max = date.min().date(), date.max().date()
        #st.info(f"📅 Dati disponibili: dal **{d_min.strftime('%d/%m/%Y')}** al **{d_max.strftime('%d/%m/%Y')}**")
        
        return d_min, d_max
        
    return None, None


def DATA_filtering(period, df):
    
    if isinstance(period, tuple) and len(period) == 2:
        #DATA_start, DATA_end = period
        df_filtrato = df[
                (df['DATA'].dt.date >= period[0]) & 
                (df['DATA'].dt.date <= period[1])
                ].copy()
        
    # Un piccolo avviso se manca una delle due date (inizio o fine)
    else:
        df_filtrato = df_events.copy()
        st.warning("Seleziona entrambe le date (inizio e fine) per filtrare.")

    return df_filtrato





def validazione_importi(df):
    if df is None or df.empty:
        st.error("DATAframe assente o vuoto!")
        return None, None

    # Creiamo una copia per evitare modifiche al DATAframe originale
    df = df.copy()

    # --- 1. PULIZIA E CALCOLO DEL TOTALE ---
    # Funzione aggiornata per trattare migliaia (.) e decimali (,)
    def converti_valore(val):
        try:
            if pd.isna(val): return 0.0
            
            # Trasformiamo in stringa e puliamo gli spazi
            val_str = str(val).strip().replace(' ', '')
            
            # LOGICA INTELLIGENTE:
            # Se ci sono sia punto che virgola (es: 1.250,50)
            if '.' in val_str and ',' in val_str:
                val_str = val_str.replace('.', '').replace(',', '.')
            # Se c'è solo la virgola (es: 400,00)
            elif ',' in val_str:
                val_str = val_str.replace(',', '.')
            # Se c'è solo il punto (es: 1.0 o 22.0)
            # NON lo rimuoviamo, perché è quasi certamente un decimale standard
            
            # Estrae solo numeri, punto decimale e segno meno
            pulito = re.sub(r'[^0-9.-]', '', val_str)
            
            return float(pulito) if pulito else 0.0
        except:
            return 0.0

    # Applichiamo la pulizia alle colonne numeriche necessarie
    for col in ['QT', 'PREZZO', 'IVA']:
        if col in df.columns:
            df[f'{col}_pulito'] = df[col].apply(converti_valore)
        else:
            df[f'{col}_pulito'] = 0.0

    # Calcolo del TOTALE: (Prezzo * Quantità) + IVA (%)
    # Formula: (P * Q) * (1 + IVA/100)
    df['TOTALE_TMP'] = (df['PREZZO_pulito'] * df['QT_pulito']) * (1 + (df['IVA_pulito'] / 100))

    # --- 2. VALIDAZIONE TIPO DOC ---
    tipi_ammessi = ["PREVENTIVO", "ORDINE APERTO", "ORDINE"]
    mask_tipo_errato = ~df['TIPOLOGIA DOC.'].astype(str).isin(tipi_ammessi)

    # --- 3. CREAZIONE MASCHERE FINALI ---
    mask_errori = (df['TOTALE_TMP'] <= 0) | (df['TOTALE_TMP'].isna()) | mask_tipo_errato

    df_errori = df[mask_errori].copy()
    df_pulito = df[~mask_errori].copy()
    
    # Assegniamo il valore calcolato alla colonna definitiva 'TOTALE'
    df_pulito['TOTALE'] = df_pulito['TOTALE_TMP']
    
    # --- 4. PULIZIA FINALE ---
    cols_da_rimuovere = ['QT_pulito', 'PREZZO_pulito', 'IVA_pulito', 'TOTALE_TMP']
    df_pulito = df_pulito.drop(columns=cols_da_rimuovere)
    df_errori = df_errori.drop(columns=cols_da_rimuovere)

    # --- DEBUG E OUTPUT ---
    st.write(f"✅ File elaborato: {len(df)} righe totali rilevate.")
    
    if len(df_errori) > 0:
        with st.expander("⚠️ ERRORI RILEVATI", expanded=False):
            st.error(f"Trovate {len(df_errori)} righe scartate (Importo non valido o Tipo Doc non ammesso)!")
            st.dataframe(df_errori)
    else:
        st.success("Nessun errore rilevato (Tutti i calcoli sono validi).")

    return df_pulito, df_errori
    

def render_grafico_torta(DATA, values_col, names_col, titolo, tipo="numerico"):
    """
    Renderizza un grafico a torta con stile fisso e ORDINE orario costante.
    """
    
    # Palette Pastello
    palette = {
        "PREVENTIVO": "#A2D2FF",  
        "ORDINE APERTO": "#B4E197", 
        "ORDINE": "#4E944F"         
    }

    # ORDINE desiderato in senso orario
    ORDINE_fisso = ["PREVENTIVO", "ORDINE APERTO", "ORDINE"]

    fig = px.pie(
        DATA, 
        values=values_col, 
        names=names_col,
        title=titolo,
        hole=0.4,
        color=names_col,
        color_discrete_map=palette,
        category_orders={names_col: ORDINE_fisso} 
    )

    if tipo == "soldi":
        testo_etichette = '%{label}<br>%{percent}<br>€%{value:,.2f}'
    else:
        testo_etichette = '%{label}<br>%{percent}<br>N. %{value}'

    fig.update_traces(
        textinfo='percent+value+label',
        texttemplate=testo_etichette,
        pull=[0.05] * len(DATA),
        marker=dict(line=dict(color='#FFFFFF', width=2)),
        sort=False 
    )

    fig.update_layout(
        height=500, 
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="center", 
            x=0.5,
            traceorder="normal"
        ),
        margin=dict(t=100, b=20, l=20, r=20),
        title_x=0.35 
    )
    
    st.plotly_chart(fig, use_container_width=True)




def plot_distribuzione_ordini(df_target):
    
    if df_target.empty:
        st.warning("Nessun dato disponibile.")
        return

    df_plot = df_target.copy()

    # Creiamo la stringa DATA PRIMA di ogni altra operazione
    if 'DATA' in df_plot.columns:
        # Convertiamo in datetime se non lo è, poi in stringa
        df_plot['DATA_Str'] = pd.to_datetime(df_plot['DATA']).dt.strftime('%d/%m/%Y')
    else:
        df_plot['DATA_Str'] = "N.D."

    if 'bin_size' not in st.session_state:
        st.session_state.bin_size = 1000
        
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.5, 0.5]
    )

    # Palette
    palette = {
        "PREVENTIVO": "#A2D2FF",    
        "ORDINE APERTO": "#B4E197", 
        "ORDINE": "#4E944F"         
    }
    stadi = ["PREVENTIVO", "ORDINE APERTO", "ORDINE"]

    for stadio in stadi:
        
        # Filtriamo il DATAframe per lo stadio attuale
        df_stadio = df_plot[df_plot['TIPOLOGIA DOC.'] == stadio]
        
        if df_stadio.empty: continue

        vals = df_stadio['TOTALE']

        # ISTOGRAMMA (Row 2)
        fig.add_trace(
            go.Histogram(
                x=vals,
                name=stadio,
                marker_color=palette[stadio],
                opacity=0.6,
                xbins=dict(size=st.session_state.bin_size),
                marker_line=dict(width=1, color='white'),
                legendgroup=stadio
            ),
            row=2, col=1
        )

        # BOXPLOT (Row 1)
        fig.add_trace(
            go.Box(
                x=vals,
                name=stadio,
                marker_color=palette[stadio],
                boxpoints='all',
                jitter=0.5,       
                pointpos=0,
                legendgroup=stadio,
                showlegend=False,
                orientation='h',
                # Passiamo i dati extra qui
                customdata=df_stadio[['DATA_Str', 'ID DOCUMENTO', 'CLIENTE', 'TITOLO', 'CODICE GESTIONALE UTENTE']],
                # Definiamo cosa appare al passaggio del mouse
                hovertemplate=(
                    "<b>TOTALE Articoli:</b> €%{x:,.2f}<br>" +
                    "<b>DATA:</b> %{customdata[0]}<br>" +
                    "<b>ID:</b> %{customdata[1]}<br>" +
                    "<b>CLIENTE:</b> %{customdata[2]}<br>" +
                    "<b>Titolo:</b> %{customdata[3]}<br>" +
                    "<b>UTENTE:</b> %{customdata[4]}<br>" +
                    "<extra></extra>" # Rimuove la scritta "trace name" a lato
                )
            ),
            row=1, col=1
        )

    fig.update_layout(
        height=1000,
        barmode='overlay',
        margin=dict(t=50, b=50, l=50, r=50),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        xaxis=dict(
            type='linear',
            exponentformat='none',
            gridcolor='lightgray'
        )
    )
    fig.update_xaxes(title_text="Importo Documento (TOTALE articoli) (€)", row=2, col=1)
    fig.update_yaxes(type="log", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

    # SLIDER FASCE DI PREZZO
    col1, col2, col3 = st.columns(3)
    with col2:
        bin_size = st.slider(
            "Seleziona le fasce di prezzo per l'istogramma (€)", 
            min_value=100, 
            max_value=10000, 
            value=1000, 
            step=100,
            format="%d €", # Forza la visualizzazione come intero seguito da €
            key="bin_size"
        )


def colora_stato(val):
    """Funzione di utilità per colorare il testo nella tabella Streamlit"""
    colori = {
        "AGGIUDICATO (CHIUSO)": "color: #4E944F; font-weight: bold;",
        "AGGIUDICATO (APERTO)": "color: #B4E197; font-weight: bold;",
        "IN SCADENZA": "color: #CCAA00; font-weight: bold;",
        "IN ATTESA": "color: #007BFF;",
        "PERSO": "color: #FF4B4B;"
    }
    return colori.get(val, "color: black;")



def analisi_conversione_preventivi(df, finestra, giorni_scadenza=7):
    # NOTA: df è già passato per validazione_importi(), quindi ha già la colonna 'TOTALE'
    
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




def analizza_performance_commerciali(df_report):
    
    # 1. PREPARAZIONE DATI
    df_integro = df_report.copy()
    if 'Analisi_Integrita' in df_report.columns:
        df_integro = df_integro[df_integro['Analisi_Integrita'] == "Dato Integro"]

    # 2. CALCOLO AGGREGATO BASE
    gruppo_agente = df_integro.groupby('CODICE GESTIONALE UTENTE')
    
    performance = gruppo_agente.agg(
        Nr_Prev=('ID DOCUMENTO', 'nunique'),
        Vol_Prev=('TOTALE', 'sum'),
        Nr_Vinti=('STATO_FINALE', lambda x: x.str.contains("AGGIUDICATO").sum()),
        Vol_Vinto=('TOTALE ORDINE', 'sum')
    ).reset_index()

    # 3. CALCOLO DETTAGLI CHIUSI/APERTI
    chiusi = df_integro[df_integro['STATO_FINALE'] == "AGGIUDICATO (CHIUSO)"].groupby('CODICE GESTIONALE UTENTE').agg(
        Nr_Chiusi=('ID DOCUMENTO', 'count'), Vol_Chiusi=('TOTALE ORDINE', 'sum')
    ).reset_index()

    aperti = df_integro[df_integro['STATO_FINALE'] == "AGGIUDICATO (APERTO)"].groupby('CODICE GESTIONALE UTENTE').agg(
        Nr_Aperti=('ID DOCUMENTO', 'count'), Vol_Aperti=('TOTALE ORDINE', 'sum')
    ).reset_index()

    performance = performance.merge(chiusi, on='CODICE GESTIONALE UTENTE', how='left').merge(aperti, on='CODICE GESTIONALE UTENTE', how='left').fillna(0)

    # 4. CALCOLO RATE NUMERICI (Per i Grafici)
    performance['Hit_Rate_Nr'] = (performance['Nr_Vinti'] / performance['Nr_Prev'] * 100).fillna(0)

    # 5. FUNZIONI FORMATTAZIONE PARENTESI (Per le Tabelle)
    def fmt_val_pct(val, total):
        pct = (val / total * 100) if total > 0 else 0
        return f"€ {val:,.2f} ({pct:.1f}%)"

    def fmt_nr_pct(val, total):
        pct = (val / total * 100) if total > 0 else 0
        return f"{int(val)} ({pct:.1f}%)"

    performance['Nr. Prev. Vinti (%)'] = performance.apply(lambda r: fmt_nr_pct(r['Nr_Vinti'], r['Nr_Prev']), axis=1)
    performance['Vol. Vinto (%)'] = performance.apply(lambda r: fmt_val_pct(r['Vol_Vinto'], r['Vol_Prev']), axis=1)
    performance['Nr. Ord. (Chiusi)'] = performance.apply(lambda r: fmt_nr_pct(r['Nr_Chiusi'], r['Nr_Vinti']), axis=1)
    performance['Vol. Ord. (Chiusi)'] = performance.apply(lambda r: fmt_val_pct(r['Vol_Chiusi'], r['Vol_Vinto']), axis=1)
    performance['Nr. Ord. (Aperti)'] = performance.apply(lambda r: fmt_nr_pct(r['Nr_Aperti'], r['Nr_Vinti']), axis=1)
    performance['Vol. Ord. (Aperti)'] = performance.apply(lambda r: fmt_val_pct(r['Vol_Aperti'], r['Vol_Vinto']), axis=1)

    # 6. VISUALIZZAZIONE TABELLA GENERALE
    st.write("")
    st.subheader("📈 Comparativa")
    st.write("")
    df_gen = performance[['CODICE GESTIONALE UTENTE', 'Nr_Prev', 'Nr. Prev. Vinti (%)', 'Vol_Prev', 'Vol. Vinto (%)', 
                          'Nr. Ord. (Chiusi)', 'Vol. Ord. (Chiusi)', 'Nr. Ord. (Aperti)', 'Vol. Ord. (Aperti)']].copy()
    df_gen.columns = ['Utente', 'Nr. Prev.', 'Nr. Prev. Vinti (%)', 'Vol. Prev.', 'Vol. Vinto (%)', 
                      'Nr. Ord. (Chiusi)', 'Vol. Ord. (Chiusi)', 'Nr. Ord. (Aperti)', 'Vol. Ord. (Aperti)']
    
    st.dataframe(df_gen.style.format({'Nr. Prev.': '{:,.0f}', 'Vol. Prev.': '€ {:,.2f}'}), use_container_width=True, hide_index=True)

    # --- 📊 SEZIONE GRAFICI COMPARATIVI (Side-by-Side) ---
    st.write("")
    col1, col2 = st.columns(2)

    with col1:
        # Grafico a Barre: Offerto vs Vinto
        fig_bar = px.bar(
            performance, 
            x='CODICE GESTIONALE UTENTE', 
            y=['Vol_Prev', 'Vol_Vinto'],
            barmode='group',
            title="Volume Preventivato vs Vinto",
            labels={'value': 'Euro (€)', 'variable': 'Tipo Volume', 'CODICE GESTIONALE UTENTE': 'Utente'},
            color_discrete_map={'Vol_Prev': '#A2D2FF', 'Vol_Vinto': '#4E944F'}
        )
        fig_bar.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        # Scatter Plot: Efficienza
        fig_scatter = px.scatter(
            performance, 
            x='Nr_Prev', 
            y='Hit_Rate_Nr',
            size='Vol_Vinto', 
            color='CODICE GESTIONALE UTENTE',
            title="Efficienza: N. Prev vs Tasso Conversione (%)",
            labels={'Nr_Prev': 'N. Preventivi', 'Hit_Rate_Nr': 'Tasso Conversione (%)', 'Vol_Vinto': 'Volume (€)'},
            template="plotly_white"
        )
        fig_scatter.update_layout(showlegend=False) # Legenda già presente nel grafico a fianco o implicita
        st.plotly_chart(fig_scatter, use_container_width=True)


    # --- 7. SEZIONE DETTAGLIO SINGOLO UTENTE ---
    st.divider()
    st.subheader("👤 Analisi Dettagliata per Utente")
    st.write("")
    
    utenti = df_report['CODICE GESTIONALE UTENTE'].unique()
    agente_sel = st.selectbox("Seleziona un Utente per approfondire:", utenti)
    
    if agente_sel:
        # Riepilogo KPI (Riga singola)
        perf_agente = performance[performance['CODICE GESTIONALE UTENTE'] == agente_sel].copy()
        df_kpi_agente = perf_agente[['Nr_Prev', 'Nr. Prev. Vinti (%)', 'Vol_Prev', 'Vol. Vinto (%)', 
                                    'Nr. Ord. (Chiusi)', 'Vol. Ord. (Chiusi)', 'Nr. Ord. (Aperti)', 'Vol. Ord. (Aperti)']].copy()
        df_kpi_agente.columns = ['Nr. Prev.', 'Nr. Prev. Vinti (%)', 'Vol. Prev.', 'Vol. Vinto (%)', 
                                 'Nr. Ord. (Chiusi)', 'Vol. Ord. (Chiusi)', 'Nr. Ord. (Aperti)', 'Vol. Ord. (Aperti)']

        st.write("")
        st.write(f"**Riepilogo Performance**")
        st.write("")
        st.dataframe(df_kpi_agente.style.format({'Nr. Prev.': '{:,.0f}', 'Vol. Prev.': '€ {:,.2f}'}), use_container_width=True, hide_index=True)

        # Registro Documenti (Analitico)
        st.write("")
        st.write(f"**Registro**")
        st.write("")
        df_agente_full = df_report[df_report['CODICE GESTIONALE UTENTE'] == agente_sel].copy()
        df_display_agente = df_agente_full[[
            'DATA', 'DATA ORDINE', 'DURATA', 'STATO_FINALE', 'INFO', 
            'CLIENTE', 'CODICE GESTIONALE UTENTE', 'QT', 'NUM ART ORD', 'TOTALE', 'TOTALE ORDINE',
            'ID DOCUMENTO', 'ID ORDINE'
        ]].copy()

        df_display_agente.columns = [
            'Data Prev.', 'Data Ord.', 'Durata', 'Stato', 'Info', 
            'Cliente', 'Utente', 'Q.tà Prev.', 'Q.tà Ord.', 'Tot. Prev.', 'Tot. Ord.', 
            'ID Prev.', 'ID Ord.'
        ]

        st.dataframe(
            df_display_agente.sort_values(by=['Data Prev.'], ascending=False)
            .style.format({
                'Data Prev.': lambda x: pd.to_datetime(x).strftime('%d/%m/%Y'),
                'Data Ord.': lambda x: pd.to_datetime(x).strftime('%d/%m/%Y') if pd.notnull(x) else "-",
                'Tot. Prev.': '{:,.2f} €',
                'Tot. Ord.': '{:,.2f} €',
                'Durata': lambda x: f"{int(x)} gg" if pd.notnull(x) else "-",
                'Q.tà Prev.': '{:,.0f}', 
                'Q.tà Ord.': '{:,.0f}'   
            }).map(colora_stato, subset=['Stato']),
            use_container_width=True, hide_index=True
        )

    return performance




# ***********************************************************************
#                                 MAIN APP
# ***********************************************************************


st.header("Analisi Commerciali")
st.divider()

# Inizializzazione
df_events = None
df_orders = None
# date calendario
date_min = None
date_max = None


# *****************
# CARICAMENTO FILE 
# *****************

# 1. Inizializzazione variabili all'inizio dello script per evitare NameError
df_events = None
df_orders = None
date_min = None
date_max = None

st.subheader("Caricamento File")
col1, col2, col3 = st.columns(3)

# --- SEZIONE EVENTI ---
with col1:
    st.write("#### Eventi")
    uploaded_file_events = st.file_uploader("Carica file eventi (formato CSV)", type="csv")
    if uploaded_file_events:
        df_events = carica_dati_eventi(uploaded_file_events) # Usa la funzione normalizzata creata prima
        if df_events is not None:
            d_min_ev, d_max_ev = DATA_range(df_events)
            date_min, date_max = d_min_ev, d_max_ev

import json
import pandas as pd
import streamlit as st

# ... (dentro il tuo MAIN APP, nella col2 degli Ordini)
with col2:
    st.write("#### Ordini")
    uploaded_file_orders = st.file_uploader("Carica file ordini (formato JSON)", type="json")
    
    if uploaded_file_orders:
        try:
            # 1. Leggiamo il file JSON grezzo
            dati_json = json.load(uploaded_file_orders)
            
            # 2. Convertiamo la struttura in una tabella "Excel-like"
            # Caso A: Il JSON è già una lista piatta di articoli/righe
            if isinstance(dati_json, list) and len(dati_json) > 0 and not isinstance(dati_json[0], (list, dict)):
                df_anteprima = pd.DataFrame(dati_json)
                
            # Caso B: Il JSON ha una struttura annidata (Documento -> Lista di Righe/Articoli)
            elif isinstance(dati_json, list) and len(dati_json) > 0:
                # Ispezioniamo il primo record per capire se c'è una lista interna (es. 'righe', 'articoli', 'items')
                chiavi_del_record = dati_json[0].keys()
                # Cerchiamo una chiave che contenga una lista (le righe del documento)
                chiave_lista_interna = next((k for k in chiavi_del_record if isinstance(dati_json[0][k], list)), None)
                
                if chiave_lista_interna:
                    # Estraiamo le altre chiavi del documento principale da replicare su ogni riga
                    chiavi_meta = [k for k in chiavi_del_record if k != chiave_lista_interna]
                    
                    # Usiamo json_normalize per "spianare" il JSON in formato Excel
                    df_anteprima = pd.json_normalize(
                        dati_json, 
                        record_path=chiave_lista_interna, 
                        meta=chiavi_meta,
                        errors='ignore'
                    )
                else:
                    # Se non ci sono liste annidate, lo convertiamo direttamente in tabella
                    df_anteprima = pd.DataFrame(dati_json)
            else:
                # Caso C: È un dizionario singolo
                df_anteprima = pd.json_normalize(dati_json)

            # --- VISUALIZZAZIONE IN FORMATO TABELLA EXCEL ---
            st.success(f"📊 JSON convertito con successo! Rilevate {df_anteprima.shape[0]} righe e {df_anteprima.shape[1]} colonne.")
            
            # Mostriamo le colonne disponibili come faresti su Excel
            st.write("### Anteprima colonne rilevate nel JSON:")
            st.write(list(df_anteprima.columns))
            
            # Mostriamo la tabella interattiva (Excel Style)
            st.dataframe(df_anteprima, use_container_width=True)
            
            # Per far funzionare il resto della tua app, ora puoi passare questo df_anteprima 
            # alla tua funzione di validazione (es. validazione_importi)
            # df_orders, df_errori = validazione_importi(df_anteprima)
            
        except Exception as e:
            st.error(f"❌ Errore nella conversione tabulare del JSON: {e}")


# --- SEZIONE FILTRO PERIODO ---
# Attiviamo i filtri solo se almeno uno dei due DF è stato creato
if date_min is not None and date_max is not None:
    with col3:
        st.write("#### Periodo Analisi")
        period = st.date_input(
            "Seleziona date:",
            value=(date_min, date_max),
            min_value=date_min,
            max_value=date_max
        )

    # Applichiamo il filtraggio solo se l'utente ha selezionato un range completo (inizio e fine)
    if isinstance(period, tuple) and len(period) == 2:
        if df_events is not None:
            df_events = DATA_filtering(period, df_events)
        
        if df_orders is not None:
            df_orders = DATA_filtering(period, df_orders)
    else:
        st.warning("Completa la selezione del periodo (Data inizio e Data fine).")
else:
    st.info("Carica almeno un file per attivare i filtri temporali.")






# ***********************************************************************
#                             ANALISI ORDINI 
# ***********************************************************************

st.divider()
st.subheader("Analisi Ordini e Preventivi")
st.write("")

if df_orders is not None: 
    
    # ************
    #   PANORAMICA
    # ************

    st.write("")
    
    # 1. COMPATTAZIONE PER ID DOCUMENTO
    # Creaiamo un DATAframe suddiviso per l'ID dei documenti.
    # Per ogni ID avremo la tipologia di documento (PREVENTIVO, ORDINE APERTO, ORDINE)
    # e il TOTALE (€) degli articoli per quel documento.
    
    df_documenti_univoci = df_orders.groupby('ID DOCUMENTO').agg({
        'TIPOLOGIA DOC.': 'first',
        'TOTALE': 'sum'
    }).reset_index()

    
    # 2. QUANTITÀ
    # Num. documenti = numero ID esistenti per ogni tipologia
    
    conteggio_qty = df_documenti_univoci['TIPOLOGIA DOC.'].value_counts().reset_index()
    conteggio_qty.columns = ['TIPOLOGIA DOC.', 'Conteggio'] 

    
    # 3. VOLUMI
    # Sommamiamo sui totali di ogni documento per ogni tipologia
    conteggio_vol = df_documenti_univoci.groupby('TIPOLOGIA DOC.')['TOTALE'].sum().reset_index()

    
    with st.expander("📊 Panoramica Quantità e Volumi"):
        
        if not conteggio_qty.empty and not conteggio_vol.empty:
            col_sinistra, col_destra = st.columns(2)

            with col_sinistra:
                render_grafico_torta(
                    DATA=conteggio_qty, 
                    values_col='Conteggio', 
                    names_col='TIPOLOGIA DOC.', 
                    titolo="N. Documenti Univoci",
                    tipo="numerico"
                )
            
            with col_destra:
                render_grafico_torta(
                    DATA=conteggio_vol, 
                    values_col='TOTALE', 
                    names_col='TIPOLOGIA DOC.', 
                    titolo="Valore Economico TOTALE",
                    tipo="soldi"
                )
        
        # 4. METRICHE
        
        # Mediana e Media sui documenti
        mediane = df_documenti_univoci.groupby('TIPOLOGIA DOC.')['TOTALE'].median().reset_index()
        mediane.columns = ['TIPOLOGIA DOC.', 'Mediana (€)']
        df_riepilogo = pd.merge(conteggio_qty, conteggio_vol, on='TIPOLOGIA DOC.')
        df_riepilogo = pd.merge(df_riepilogo, mediane, on='TIPOLOGIA DOC.')
        
        # Percentuali
        tot_qty = df_riepilogo['Conteggio'].sum()
        tot_vol = df_riepilogo['TOTALE'].sum()
        df_riepilogo['% Qty'] = (df_riepilogo['Conteggio'] / tot_qty * 100).round(1).astype(str) + '%'
        df_riepilogo['% Vol'] = (df_riepilogo['TOTALE'] / tot_vol * 100).round(1).astype(str) + '%'
        
        # Prezzo Medio per ORDINE Completo
        df_riepilogo['Media (€)'] = (df_riepilogo['TOTALE'] / df_riepilogo['Conteggio'])
        
        # Ordinamento e formattazione nomi (TUTTO MAIUSCOLO per le colonne)
        ORDINE_fisso = ["PREVENTIVO", "ORDINE APERTO", "ORDINE"]
        df_riepilogo['TIPOLOGIA DOC.'] = pd.Categorical(df_riepilogo['TIPOLOGIA DOC.'], categories=ORDINE_fisso, ordered=True)
        df_riepilogo = df_riepilogo.sort_values('TIPOLOGIA DOC.')
        
        colonne_finali = [
            'TIPOLOGIA DOC.', 'Conteggio', '% Qty', 
            'TOTALE', '% Vol', 'Media (€)', 'Mediana (€)'
        ]

        st.write("")
        st.dataframe(
            df_riepilogo[colonne_finali].style.format({
                'TOTALE': '€ {:,.2f}',
                'Media (€)': '€ {:,.2f}',
                'Mediana (€)': '€ {:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        st.caption("Nota: I dati sopra riportati sono raggruppati per **ID DOCUMENTO**. Il valore 'TOTALE' è la somma degli importi di tutte le righe del documento.")
        
        # Istogramma e BoxPlot della distribuzione articoli
        st.divider()
        st.write("#### Distribuzione Ordini e Preventivi")
        st.info("""
        **Come leggere questo grafico:**
        * **Istogramma:** Indica le fasce di prezzo dove si concentrano i tuoi volumi.
        * **Box Plot:** La linea centrale è la **Mediana**. I punti isolati sono gli **Outliers** (⚠️ ordini eccezionalmente grandi -> verificare).
        """)
        plot_distribuzione_ordini(df_orders)
        
       
    # **********************************
    #  CONVERSIONE PREVENTIVI - GLOBALE
    # **********************************

    st.write("")
    with st.expander("🎯 Analisi Conversione Preventivi Globale"):
        st.write("")
        with st.popover("ℹ️ Guida all'Analisi"):
            st.info("""
            #### Classificazione (STATO)
            Il sistema classifica ogni preventivo come segue:
        
            *   🟢 **AGGIUDICATO (CHIUSO)**: Il preventivo è stato convertito in un **Ordine**. 
            *   🟢 **AGGIUDICATO (APERTO)**: Il preventivo è stato convertito in un **Ordine Aperto**.
            *   🔵 **IN ATTESA**: Il preventivo si trova ancora all'interno della finestra di conversione.
            *   🟠 **IN SCADENZA**: Ordine vicino alla fine della finestra di conversione.
            *   🔴 **PERSO**: Non è stato trovato alcun ordine collegato **e** il tempo trascorso ha superato la finestra impostata.
            
            ---
    
            #### Dettagli Conversione (INFO)
            Analisi della qualità della vendita confrontando articoli e quantità tra preventivo e ordine:
        
            *   ✅ **INTEGRALE**: Tutti gli articoli preventivati sono stati ordinati nelle quantità esatte.
            *   ⚠️ **INCOMPLETO**: Uno o più articoli presenti nel preventivo non sono stati inclusi nell'ordine finale.
            *   📉 **RIDOTTO**: Tutti gli articoli presenti, ma almeno uno ha una quantità inferiore rispetto al preventivo.
            *   🚀 **EXTRA**: L'ordine ha un volume economico maggiore o contiene più pezzi/articoli rispetto al preventivo (Upsell).
            *   📦 **MULTI-TRANCHE**: Il preventivo è stato convertito attraverso due o più ordini separati.
        
            **Combinazioni Comuni:**
            *   🧩 **INCOMPLETO + RIDOTTO**: Il cliente ha rimosso alcuni articoli e, per quelli rimasti, ha anche abbassato le quantità.
            *   🧩 **INCOMPLETO + EXTRA**: Mancano alcuni articoli originali, ma l'ordine ha un valore totale (€) maggiore (es. un articolo rimasto è stato venduto in quantità massiccia o a prezzo maggiorato).
            *   🧩 **RIDOTTO + EXTRA**: Le quantità di alcuni articoli sono scese, ma il valore totale (€) è comunque superiore al preventivo (es. aggiunta di articoli extra).
            *   🧩 **EXTRA + MULTI-TRANCHE**: Il preventivo è stato evaso con più ordini che, sommati, superano il valore o le quantità preventivate.
            *   🧩 **RIDOTTO + MULTI-TRANCHE**: La fornitura sta avvenendo a scaglioni e, al momento, le quantità totali sono ancora inferiori al preventivato.
        
            ---
            #### Metriche
            *   **Durata**: 
                *   Per gli AGGIUDICATI, indica i giorni reali tra preventivo e ordine 
                    (nel caso di ordine in più tranche, considera per la data e la durata l'ultimo ordine trovato).
                *   Per gli ALTRI STATI, indica i giorni passati dalla creazione ad oggi.
            *   **Q.tà Prev. / Q.tà Ord.**: Somma totale degli articoli nei documenti (articoli x num. pezzi). Utile per vedere se l'ordine ha coperto tutto il preventivato.
            *   **Conversione**: Un preventivo è AGGIUDICATO se almeno un ID di un articolo del preventivo è stato ritrovato in un Ordine, 
                               anche se oltre la finestra di validità dei preventivi. 
            """)
        st.write("")
        st.write("")

        # --- CALCOLO MASSIMO DINAMICO ---
        # Se period è una tupla con due date (inizio e fine)
        if isinstance(period, tuple) and len(period) == 2:
            delta_giorni = (period[1] - period[0]).days
            # Evitiamo che il max_value sia 0 se le date coincidono
            max_slider = max(1, delta_giorni)
        else:
            max_slider = 180 # Valore di fallback
        # --------------------------------
        
        # Creiamo due colonne per i parametri
        c1, c2, c3, c4, c5 = st.columns([0.2, 1, 0.3, 1, 0.2])
        
        with c2:
            finestra = st.slider(
                "Validità preventivi (giorni):", 
                min_value=1, max_value=max_slider, value=30, 
                help="Giorni massimi per convertire un PREVENTIVO in ORDINE."
            )
        
        with c4:
            scadenza = st.number_input(
                "Pre-avviso 'In Scadenza' (giorni):", 
                min_value=1, max_value=30, value=7,
                help="Giorni prima della scadenza per attivare l'avviso GIALLO."
            )
        
        # Chiamata alla funzione aggiornata
        st.write("")
        st.write("")
        df_report = analisi_conversione_preventivi(df_orders, finestra, scadenza)


    # ******************************************
    #  CONVERSIONE PREVENTIVI - PER COMMERCIALE
    # ******************************************

    st.write("")
    with st.expander("🏆 Analisi Conversione Preventivi per Commerciale"):
        df_performance = analizza_performance_commerciali(df_report)
    




if df_events is not None:
    
    # PANORAMICA EVENTI ---
    st.divider()
    st.subheader("Analisi Eventi")
    with st.expander("👁️ Panoramica Eventi"):
        distribuzione_eventi(df_events)


    # PERFORMANCE TEAM ---
    st.write("")
    st.write("")
    with st.expander("⚡️ Performance Team"):
        analisi_performance_utenti(df_events)

    
    # --- SEZIONE AZIENDE PIÙ COINVOLTE ---
    st.write("")
    st.write("")
    with st.expander("🏢 Analisi Coinvolgimento Aziende"):
        coinvolgimento_aziende(df_events)
        
