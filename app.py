import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import re
import numpy as np

st.set_page_config(layout="wide")

@st.cache_data
def carica_dati_commerciali(file):
    
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
                    "<b>Utente:</b> %{customdata[4]}<br>" +
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



def analisi_conversione_preventivi(df, finestra, giorni_scadenza=7):
    
    # 1. SEPARAZIONE DEI DATAFRAME
    preventivi = df[df['TIPOLOGIA DOC.'] == "PREVENTIVO"].copy()
    ordini     = df[df['TIPOLOGIA DOC.'].isin(["ORDINE", "ORDINE APERTO"])].copy()

    if preventivi.empty:
        st.warning("⚠️ Nessun PREVENTIVO trovato!")
        return None

    DATA_riferimento = df['DATA'].max()

    # 2. CROSS-JOIN TECNICO TRAMITE TRACK ID
    # Creiamo i collegamenti tra articoli offerti e venduti basandoci sul TRACK ID
    merged = pd.merge(
        preventivi, 
        ordini[['TRACK ID', 'ID DOCUMENTO', 'DATA', 'TIPOLOGIA DOC.']], # Selezioniamo solo le colonne dell'ordine necessarie per il match e la datazione
        on='TRACK ID',                 # Il TRACK ID è la chiave univoca che lega l'articolo nelle varie fasi
        how='left',                    # 'left' mantiene TUTTI i preventivi (anche quelli non convertiti in ordine)
        suffixes=('_prev', '_ord')     # Rinoma le colonne omonime (DATA, ID DOCUMENTO) per distinguerne l'origine
    )

    # --- CALCOLO LEAD TIME (FINESTRA DI CONVERSIONE) ---
    # Calcoliamo la differenza temporale (in giorni) tra preventivo 
    # e l'emissione dell'ordine per ogni singolo articolo tracciato.
    # I valori risultanti saranno:
    # - Positivi/Zero: Ordine regolare (avvenuto lo stesso giorno o dopo)
    # - NaN (nulli): Preventivi non ancora convertiti (In Attesa o Persi)
    merged['diff_giorni'] = (merged['DATA_ord'] - merged['DATA_prev']).dt.days

    # 3. VALUTAZIONE STATO DETTAGLIATO (Completo, Parziale, Extra)
    def definisci_stato_documento(group):

        # IDENTIFICAZIONE DEGLI ARTICOLI EFFETTIVAMENTE VENDUTI
        # Scarta le righe (articoli) del preventivo che non hanno trovato un corrispettivo nell'ordine 
        #    (dove 'ID DOCUMENTO_ord' è rimasto vuoto/NaN dopo il left join).
        # Mantiene solo le righe "evase", ovvero quelle che hanno un ID ordine valido.
        righe_evase = group[group['ID DOCUMENTO_ord'].notna()]

        # Se nessun articolo è stato evaso, ritorna None
        if righe_evase.empty:
            return pd.Series([None, None, None, None]) 

        # CONTROLLO FINESTRA TEMPORALE
        # Verifica se il primo articolo del preventivo è stato convertito entro i giorni stabiliti.
        # (.min() recupera la data del primo ordine utile associato a questo preventivo, nel
        # caso di un preventivo completato in più ordini). 
        # In caso contrario flagga l'ordine con FINISH per non tornarci
        diff_gg = righe_evase['diff_giorni'].min()
        if diff_gg > finestra:
            return pd.Series(["ORDINE FUORI FINESTRA", diff_gg, righe_evase['ID DOCUMENTO_ord'].iloc[0], "FINISH"])

        # DETERMINAZIONE DELLO STATO DOCUMENTALE
        # Identifichiamo la natura del primo ordine che ha convertito il preventivo.
        # 1. Ordiniamo per data (diff_giorni) e prendiamo il primo evento cronologico (.iloc[0]).
        # 2. Assegniamo un suffisso descrittivo per distinguere se la vendita è 
        #    già finalizzata (CHIUSO) o ancora in corso (APERTO).
        tipo_doc_ord = righe_evase.sort_values('diff_giorni')['TIPOLOGIA DOC._ord'].iloc[0]
        suffix = " (CHIUSO)" if tipo_doc_ord == "ORDINE" else " (APERTO)"

        # IDENTIFICAZIONE DEL DOCUMENTO DI CONVERSIONE (IL "VINCITORE")
        # Poiché un preventivo può essere evaso da più ordini nel tempo, 
        # dobbiamo isolare quello che ha fatto scattare la vendita per primo.
        # 1. Ordiniamo le righe evase per giorni di differenza (dal più rapido al più lento).
        # 2. .iloc[0] preleva l'ID del primo documento che ha agganciato i TRACK ID.
        # Questo ID verrà usato per determinare se sono stati aggiunti articoli extra (Upselling).
        id_ordine_vincitore = righe_evase.sort_values('diff_giorni')['ID DOCUMENTO_ord'].iloc[0]
        
        # Raccolgo tutti gli ID unici degli ordini che hanno evaso questo preventivo
        tutti_gli_ordini = ", ".join(righe_evase['ID DOCUMENTO_ord'].unique().astype(str))

        # CALCOLO DELLA CORRISPONDENZA E DELL'UPSELLING
        # Creiamo due set per confrontare i contenuti dei documenti:
        # 1.Recuperiamo tutti i TRACK ID (articoli) presenti nel preventivo originale.
        track_prev = set(group['TRACK ID'].unique())
        
        # 2. Recuperiamo TUTTI gli articoli contenuti nell'ordine "vincitore", 
        #    andando a rileggere l'intero database ordini per quell'ID documento specifico.
        track_ord_effettivi = set(ordini[ordini['ID DOCUMENTO'] == id_ordine_vincitore]['TRACK ID'].unique())
        
        # Identifichiamo quali articoli del preventivo sono stati effettivamente comprati.
        articoli_matchati = track_prev.intersection(track_ord_effettivi)

        # Verifichiamo se l'ordine contiene articoli che NON erano nel preventivo.
        # 'issubset' controlla se l'ordine è un "sottoinsieme" perfetto del preventivo.
        # Se NON lo è (not), significa che il cliente ha aggiunto prodotti extra (Upselling).
        ha_extra = not track_ord_effettivi.issubset(track_prev)

        # Se abbiamo coperto l'intera proposta commerciale...
        if len(articoli_matchati) >= len(track_prev):
            # ESEMPIO ORDINE COMPLETO: Offerto {A, B} -> Venduto {A, B}. 
            # (len è uguale, ha_extra è False)
            # ESEMPIO ORDINE CON EXTRA: Offerto {A, B} -> Venduto {A, B, C}. 
            # (len matchati è uguale a preventivo, ma ha_extra è True perché c'è C)
            stato = "ORDINE CON EXTRA" if ha_extra else "ORDINE COMPLETO"
        else:
            # ESEMPIO ORDINE PARZIALE: Offerto {A, B} -> Venduto {A}.
            # (Il numero di match è inferiore all'offerta originale)
            stato = "ORDINE PARZIALE"
            
        return pd.Series([stato + suffix, diff_gg, tutti_gli_ordini, "FINISH"])

    # APPLICAZIONE RAGGRUPPAMENTO
    # Applica la funzione "definisci_stato_documento" e salva i vari stati come segue:
    #      ID DOCUMENTO       Il numero del preventivo originale
    #      STATO_DETTAGLIO    L'etichetta (es. ORDINE COMPLETO (CHIUSO))
    #      DURATA             I giorni impiegati per la conversione
    #      ID_ORDINI_MATCH    Tutti i numeri d'ordine legati a questo preventivo
    #      PROCESSO_LOGICO    Flag FINISH per indicare la fine dell'analisi
    risultati = merged.groupby('ID DOCUMENTO_prev').apply(definisci_stato_documento).reset_index()
    risultati.columns = ['ID DOCUMENTO', 'STATO_DETTAGLIO', 'DURATA', 'ID_ORDINI_MATCH', 'PROCESSO_LOGICO']

    # 4. REPORT PREVENTIVI
    report_prev = preventivi.groupby('ID DOCUMENTO').agg({
        'DATA': 'first', 'CLIENTE': 'first', 'TOTALE': 'sum', 'CODICE GESTIONALE UTENTE': 'first'
    }).reset_index()
    report_prev = pd.merge(report_prev, risultati, on='ID DOCUMENTO', how='left')

    # 5. GESTIONE STATI TEMPORALI
    def pulizia_stati(row):
        if pd.notna(row['STATO_DETTAGLIO']): return row['STATO_DETTAGLIO']
        giorni_passati = (DATA_riferimento - row['DATA']).days
        if giorni_passati > finestra: return "PERSI"
        if (finestra - giorni_passati) <= giorni_scadenza: return "IN SCADENZA"
        return "IN ATTESA"

    report_prev['STATO'] = report_prev.apply(pulizia_stati, axis=1)

    # 6. IDENTIFICAZIONE ORDINI DIRETTI (ORFANI)
    # Questa sezione serve a recuperare gli ordini che non sono nati da un preventivo (vendite dirette).
    
    # Creiamo un set (contenitore univoco) di tutti gli ID ordine che sono già stati associati a un preventivo.
    # Usiamo .split(", ") perché 'ID_ORDINI_MATCH' può contenere più ID per riga (es. "ORD1, ORD2").
    id_matchati_totali = set()
    risultati['ID_ORDINI_MATCH'].dropna().str.split(", ").apply(id_matchati_totali.update)
    
    # Raggruppiamo il database degli ordini per avere una riga per ogni documento (testata dell'ordine).
    # Calcoliamo il totale e recuperiamo i dati principali del cliente.
    ordini_testata = ordini.groupby(['ID DOCUMENTO', 'TIPOLOGIA DOC.']).agg({
        'DATA': 'first', 'CLIENTE': 'first', 'TOTALE': 'sum', 'CODICE GESTIONALE UTENTE': 'first'
    }).reset_index()

    def definisci_ordini_diretti(row):
        # Se l'ID dell'ordine è presente nel set degli "ID_matchati", significa che ha un preventivo alle spalle.
        # Lo marchiamo come "MATCHATO" per poterlo escludere tra poco.
        if str(row['ID DOCUMENTO']) in id_matchati_totali: return "MATCHATO"
        
        # Se non è presente, è un ORDINE DIRETTO (orfano). 
        # Aggiungiamo il suffisso per sapere se è già stato evaso (CHIUSO) o è ancora un impegno (APERTO).
        suffix = " (CHIUSO)" if row['TIPOLOGIA DOC.'] == "ORDINE" else " (APERTO)"
        return "ORDINE DIRETTO" + suffix

    # Applichiamo la funzione per etichettare ogni ordine.
    ordini_testata['STATO'] = ordini_testata.apply(definisci_ordini_diretti, axis=1)
    
    # Creiamo un DataFrame che contiene solo gli ordini che NON hanno un preventivo collegato.
    ordini_diretti = ordini_testata[ordini_testata['STATO'] != "MATCHATO"].copy()

    # --- UNIONE FINALE ---
    # Uniamo i due report: quello dei preventivi (con i loro stati) e quello degli ordini diretti.
    # Il risultato sarà una tabella completa che mostra tutto il flusso commerciale dell'azienda.
    report_completo = pd.concat([report_prev, ordini_diretti], ignore_index=True)
    
    return report_completo

    

    # --- CALCOLI PER FUNNEL ---
    # Definiamo quali stati nel report sono considerati "Vinti"
    stati_vinti = ["ORDINE COMPLETO", "ORDINE CON EXTRA", "ORDINE PARZIALE"]
    
    # Filtriamo i preventivi conclusi (vinti o persi)
    df_conclusi = report_prev[report_prev['STATO'].isin(stati_vinti + ["PERSI"])]
    
    n_conclusi    = len(df_conclusi)
    val_conclusi  = df_conclusi['TOTALE'].sum()
    
    # Conteggio totali vinti
    df_vinti      = report_prev[report_prev['STATO'].isin(stati_vinti)]
    n_vinti_tot   = len(df_vinti)
    val_vinti_tot = df_vinti['TOTALE'].sum()

    # --- VISUALIZZAZIONE GRAFICI ---
    st.subheader("📊 Analisi Performance Conversioni")
    
    # Mappa colori basata direttamente sui valori della colonna STATO
    color_map_stato = {
        "ORDINE COMPLETO": "#4E944F",
        "ORDINE CON EXTRA": "#1E5631",
        "ORDINE PARZIALE": "#B4E197",
        "IN SCADENZA": "#FFD700",
        "IN ATTESA": "#A2D2FF",
        "PERSI": "#FF9999",
        "CHIUSO FUORI FINESTRA": "#7A7A7A"
    }

    r1_c1, r1_c2 = st.columns(2)
    with r1_c1:
        # Grafico basato sulla colonna STATO originale
        stats_n = report_prev['STATO'].value_counts().reset_index()
        fig_pie_n = px.pie(stats_n, values='count', names='STATO', 
                          title="Esito per Numero Documenti", hole=0.4, 
                          color='STATO', color_discrete_map=color_map_stato)
        fig_pie_n.update_layout(legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"))
        st.plotly_chart(fig_pie_n, use_container_width=True)
        
    with r1_c2:
        stats_val = report_prev.groupby('STATO')['TOTALE'].sum().reset_index()
        fig_pie_val = px.pie(stats_val, values='TOTALE', names='STATO', 
                            title="Esito per Valore Economico (€)", hole=0.4, 
                            color='STATO', color_discrete_map=color_map_stato)
        fig_pie_val.update_traces(textinfo='percent', hovertemplate='€%{value:,.2f}')
        fig_pie_val.update_layout(legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"))
        st.plotly_chart(fig_pie_val, use_container_width=True)

    # ... [Resto del codice per Funnel e Metriche (usando n_vinti_tot e val_vinti_tot)] ...

    # Funnel di conversione
    st.write("#### 🌪️ Funnel di Efficacia Commerciale")
    r2_c1, r2_c2 = st.columns(2)
    
    with r2_c1:
        fig_f_n = go.Figure(go.Funnel(
            y=["Preventivi Conclusi", "Totale Aggiudicati"], 
            x=[n_conclusi, n_vinti_tot],
            textinfo="value+percent initial", 
            marker={"color": ["#D3D3D3", "#4E944F"]}
        ))
        fig_f_n.update_layout(title="Conversione (N. Documenti)", height=300)
        st.plotly_chart(fig_f_n, use_container_width=True)
        
    with r2_c2:
        fig_f_v = go.Figure(go.Funnel(
            y=["Volume Concluso", "Volume Aggiudicato"], 
            x=[val_conclusi, val_vinti_tot],
            textinfo="value+percent initial", 
            marker={"color": ["#D3D3D3", "#4E944F"]}
        ))
        fig_f_v.update_layout(title="Conversione (Valore €)", height=300)
        st.plotly_chart(fig_f_v, use_container_width=True)

    # --- RIEPILOGO METRICHE ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTALE Emesso", f"€ {report_prev['TOTALE'].sum():,.2f}")
    m2.metric("Vinto Reale", f"€ {val_vinti_tot:,.2f}", f"{n_vinti_tot} Doc")
    
    t_n = (n_vinti_tot / n_conclusi * 100) if n_conclusi > 0 else 0
    t_v = (val_vinti_tot / val_conclusi * 100) if val_conclusi > 0 else 0
    m3.metric("Tasso Conversione", f"{t_n:.1f}%", f"{t_v:.1f}% Valore")
    
    n_scad = len(report_prev[report_prev['STATO'] == "IN SCADENZA"])
    val_scad = report_prev[report_prev['STATO'] == "IN SCADENZA"]['TOTALE'].sum()
    m4.metric("In Scadenza", f"{n_scad} Doc", f"€ {val_scad:,.2f}", delta_color="inverse")

    # --- REGISTRO FINALE ---
    with st.expander("📋 Registro Dettagliato Analisi TRACK ID", expanded=True):
        # Preparazione DataFrame per visualizzazione
        df_display = report_prev[['DATA', 'CLIENTE', 'TOTALE', 'STATO', 'DURATA', 'ID_ORDINE_MATCH']].copy()
        df_display = df_display.rename(columns={'DATA': 'DATA PREV.', 'ID_ORDINE_MATCH': 'ORDINE RIF.'})
        
        # Ordinamento logico: Prima le scadenze, poi i chiusi, poi il resto
        prio = {
            "IN SCADENZA": 0, 
            "ORDINE COMPLETO": 1, 
            "ORDINE CON EXTRA": 1, 
            "ORDINE PARZIALE": 2, 
            "IN ATTESA": 3, 
            "PERSI": 4,
            "CHIUSO FUORI FINESTRA": 5
        }
        df_display['p'] = df_display['STATO'].map(prio).fillna(6)
        df_display = df_display.sort_values(['p', 'DATA PREV.'], ascending=[True, False]).drop(columns='p')
    
        def style_stato(val):
            if val == 'ORDINE COMPLETO': return 'color: #4E944F; font-weight: bold'
            if val == 'ORDINE CON EXTRA': return 'color: #1E5631; font-weight: bold'
            if val == 'ORDINE PARZIALE': return 'color: #B4E197; font-weight: bold'
            if val == 'IN SCADENZA': return 'color: #CCAA00; font-weight: bold' 
            if val == 'PERSI': return 'color: #FF9999'
            if val == 'CHIUSO FUORI FINESTRA': return 'color: #7A7A7A; font-style: italic'
            return 'color: #A2D2FF'
    
        st.dataframe(
            df_display.style.format({
                'DATA PREV.': lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else "",
                'TOTALE': '{:,.2f} €',
                'DURATA': lambda x: f"{x:.0f} gg" if pd.notnull(x) else "-"
            }).map(style_stato, subset=['STATO']),
            use_container_width=True, hide_index=True
        )

    return report_completo



def analizza_performance_commerciali(df_report):
    """
    Analizza il report completo per valutare l'efficienza di ogni commerciale.
    Filtra le anomalie per calcolare tassi di conversione realistici.
    """
    st.header("🏆 Analisi Performance per Commerciale")

    # 1. PREPARAZIONE DATI
    # Consideriamo "In Scadenza", "In Attesa" e "Persi" come preventivi non ancora vinti
    # Consideriamo "Aggiudicati" (Aperti + Chiusi) come successi
    
    # Filtriamo il DATAframe per considerare solo i dati integri nei calcoli di conversione
    df_integro = df_report[df_report['Analisi_Integrita'] == "Dato Integro"].copy()

    # 2. CALCOLO METRICHE AGGREGATE
    # Raggruppiamo per il codice gestionale dell'utente
    performance = df_integro.groupby('CODICE GESTIONALE UTENTE').agg(
        Nr_Preventivi    = ('TOTALE', 'count'),
        Volume_Offerto   = ('TOTALE', 'sum'),
        Nr_Vinti         = ('Stato_Torta', lambda x: (x == "Aggiudicati").sum()),
        Volume_Vinto     = ('TOTALE', lambda x: x[df_integro.loc[x.index, 'Stato_Torta'] == "Aggiudicati"].sum())
    ).reset_index()

    # Calcolo Tassi di Conversione (Hit Rate)
    performance['Conversion_Rate_Nr']  = (performance['Nr_Vinti'] / performance['Nr_Preventivi'] * 100).fillna(0)
    performance['Conversion_Rate_Val'] = (performance['Volume_Vinto'] / performance['Volume_Offerto'] * 100).fillna(0)

    # --- RIORDINAMENTO COLONNE ---
    # Impostiamo l'ORDINE richiesto: Nr_Preventivi, Nr_Vinti, Nr_Rate, Vol_Preventivi, Vol_Vinto, Vol_Rate
    ORDINE_colonne = [
        'CODICE GESTIONALE UTENTE', 
        'Nr_Preventivi', 
        'Nr_Vinti', 
        'Nr_Rate', 
        'Vol_Preventivi', 
        'Vol_Vinto', 
        'Vol_Rate'
    ]
    performance = performance[ORDINE_colonne]

    # 3. ANALISI DISCIPLINARE (ANOMALIE)
    anomalie_count = df_report[df_report['Analisi_Integrita'] != "Dato Integro"].groupby(
        ['CODICE GESTIONALE UTENTE', 'Analisi_Integrita']
    ).size().unstack(fill_value=0).reset_index()

    # 4. VISUALIZZAZIONE STREAMLIT
    st.subheader("📈 KPI di Conversione (Solo Dati Integri)")
    st.write("Questa tabella mostra l'efficacia reale escludendo errori di inserimento o ordini orfani.")
    
    # Visualizzazione con formattazione e colori
    st.dataframe(
        performance.style.format({
            'Nr_Rate': '{:.1f} %',
            'Vol_Preventivi': '€ {:,.2f}',
            'Vol_Vinto': '€ {:,.2f}',
            'Vol_Rate': '{:.1f} %'
        }).background_gradient(subset=['Nr_Rate'], cmap='Greens'),
        use_container_width=True, hide_index=True
    )

    # --- Tabella Qualità Dati ---
    st.divider()
    st.subheader("🚩 Analisi Qualità Inserimento Dati")
    st.write("Riepilogo delle anomalie tracciate per ogni commerciale. Alti valori qui indicano processi gestionali da rivedere.")
    
    if not anomalie_count.empty:
        st.DATAframe(anomalie_count, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Nessuna anomalia rilevata per i commerciali!")

    # --- Dettaglio Singolo Agente ---
    st.divider()
    agente_sel = st.selectbox("Seleziona un commerciale per il dettaglio righe:", df_report['CODICE GESTIONALE UTENTE'].unique())
    
    if agente_sel:
        df_agente = df_report[df_report['CODICE GESTIONALE UTENTE'] == agente_sel]
        
        col1, col2 = st.columns(2)
        col1.metric("TOTALE Righe Gestite", len(df_agente))
        col2.metric("Di cui Integre", len(df_agente[df_agente['Analisi_Integrita'] == "Dato Integro"]))
        
        st.dataframe(
            df_agente[['DATA', 'CLIENTE', 'ARTICOLO', 'TOTALE', 'Stato', 'Analisi_Integrita']],
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

st.subheader("Caricamento File")
col1, col2, col3 = st.columns(3)

# EVENTI
with col1:
    st.write("#### Eventi")
    uploaded_file_events = st.file_uploader("Carica file eventi (formato CSV)", type="csv")
    if uploaded_file_events:
        df_events = carica_dati_commerciali(uploaded_file_events)
        date_min, date_max = DATA_range(df_events)

# ORDINI
with col2:
    st.write("#### Ordini")
    uploaded_file_orders = st.file_uploader("Carica file ordini e preventivi (formato CSV)", type="csv")
    
if uploaded_file_orders:
    df_raw = carica_dati_commerciali(uploaded_file_orders)
    
    # Check importi
    if df_raw is not None:
        df_orders, df_errori = validazione_importi(df_raw)
        if df_orders is not None:
            st.write(f"✅ Validazione conclusa: {len(df_orders)} righe pulite, {len(df_errori)} scartate.")
    else:
        st.error("Il caricamento del file ha restituito None. Controlla il formato del CSV.")

    # Range date
    date_min, date_max = DATA_range(df_orders)
        

# ***************
# FILTRO PERIODO 
# ***************

# Eseguiamo il filtro solo se almeno un file è caricato

if date_min and date_max:

    with col3:
        st.write("#### Periodo Analisi")
        period = st.date_input(
            "Seleziona date:",
            value=(date_min, date_max),
            min_value = date_min,
            max_value = date_max
        )

    if df_events is not None:
        df_events = DATA_filtering(period, df_events)

    if df_orders is not None:
        df_orders = DATA_filtering(period, df_orders)
        
else:
    st.info("Carica almeno un file per attivare i filtri temporali.")




# ***********************************************************************
#                             ANALISI ORDINI 
# ***********************************************************************

st.divider()
st.subheader("💰 Analisi Ordini e Preventivi")
st.write("")

if df_orders is not None: 
    
    # ************
    #   PANORAMICA
    # ************

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

    with st.expander("🎯 Analisi Globale della Conversione dei Preventivi"):
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
    
    with st.expander("🎯 Analisi Conversione dei Preventivi per Commerciale"):
        df_performance = analizza_performance_commerciali(df_report)
    



if uploaded_file_events:
    df_events = carica_dati_commerciali(uploaded_file_events)
    
    if df_events is not None:
        
        # --- SEZIONE 2: RESOCONTO ---
        st.divider()
        with st.expander("⚖️ Volume e Tipologia Eventi"):
        
            # --- PREPARAZIONE DATI ---
            # 1. Dati per Tipologia
            stats_tipo = df_filtrato['Tipo Evento'].value_counts().reset_index()
            stats_tipo.columns = ['Tipo Evento', 'Conteggio']
            
            # 2. Dati per Qualità Note
            df_qualita = df_filtrato.copy()
            df_qualita['Qualità'] = df_qualita['Note'].apply(
                lambda x: "UTILE (Con Note)" if pd.notnull(x) and str(x).strip() != "" else "MUTO (Senza Note)"
            )
            stats_qualita = df_qualita['Qualità'].value_counts().reset_index()
            stats_qualita.columns = ['Stato Nota', 'Conteggio']
            
            # --- PRIMA RIGA: GRAFICO A TORTA TIPOLOGIE ---
            col1, col2, col3 = st.columns([2.5, 1.5, 0.25]) 
            with col1:
                st.write("#### Tipologie Eventi")
                fig_pie_tipo = px.pie(
                    stats_tipo, 
                    values='Conteggio', 
                    names='Tipo Evento', 
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_pie_tipo.update_traces(textinfo='percent+label')
             
                fig_pie_tipo.update_layout(
                    # Riduciamo i margini esterni del grafico per eliminare il bianco
                    margin=dict(t=30, l=10, r=10, b=10), 
                    
                    # GESTIONE LEGENDA (Non coloraxis)
                    legend=dict(
                        orientation="h",      # Legenda orizzontale
                        yanchor="bottom",     # Ancorata al fondo della legenda
                        y=1.02,               # Posizionata appena sopra il grafico (1.0 è il limite)
                        xanchor="center",     # Centrata orizzontalmente
                        x=0.5
                    ),
                    height=450 # Altezza fissa per evitare che si allunghi troppo
                )
                st.plotly_chart(fig_pie_tipo, use_container_width=True)

            with col2: 
                st.write("#### Vulume Eventi")
                TOTALE_attivita = len(df_filtrato)
                st.write("")
                st.metric("TOTALE Attività", TOTALE_attivita)
                st.DATAframe(stats_tipo, hide_index=True, use_container_width=True)

            with col3:
                st.write("")

            # --- SECONDA RIGA (DENTRO L'EXPANDER): COUNTPLOT ---
            st.write("")
            st.write("")
            st.write("#### Confronto Volumi per Tipologia")
            
            # Ordiniamo i dati per una visualizzazione migliore (dal più frequente al meno)
            stats_tipo_sorted = stats_tipo.sort_values(by='Conteggio', ascending=False)
            
            fig_count = px.bar(
                stats_tipo_sorted,
                x='Tipo Evento',
                y='Conteggio',
                text='Conteggio',
                color='Tipo Evento',
                color_discrete_sequence=px.colors.qualitative.Pastel,
                labels={'Conteggio': 'Numero di Attività', 'Tipo Evento': ''}
            )
            
            fig_count.update_traces(
                textposition='outside',
                cliponaxis=False # Evita che il testo sopra le barre venga tagliato
            )
            
            fig_count.update_layout(
                showlegend=False, # Inutile avendo già le etichette sull'asse X
                margin=dict(t=30, l=10, r=10, b=10),
                height=400,
                xaxis={'categoryorder':'total descending'}
            )
            
            st.plotly_chart(fig_count, use_container_width=True)

            

        # --- QUALITÀ NOTE E PERCENTUALE ---
        st.write("")
        with st.expander("💎 Qualità Eventi"):
            st.write("Controlliamo la qualità degli eventi inseriti per evitare la problematica: *Garbage In, Garbage Out* (**GIGO**)")
            st.write("")
            st.write("### Analisi *Mutismo*")
            st.info("""
                    ⚠️ Se gli eventi sono privi della nota descrittiva, non apportano contenuto informativo ma aggiungo confusione (Eventi MUTI).
                    * 💡*Tip 1:* tenere traccia della mole di questi eventi e individuarne le cause.
                    * 💡*Tip 2:* mettere un vincolo nel CRM per cui eventi senza note non possono essere caricati.
                    """)
            st.write("")

            # Creazione delle due colonne
            col_stats, col_grafico = st.columns([1, 1.5])
        
            with col_stats:

                st.write("")
                st.write("")
                st.write("")
                st.write("")
                # Piccolo istogramma per il confronto rapido dei volumi
                fig_bar_qual = px.bar(
                    stats_qualita,
                    x='Stato Nota',
                    y='Conteggio',
                    text='Conteggio',
                    color='Stato Nota',
                    color_discrete_map={
                        "UTILI (Con Note)": "#2ecc71", 
                        "MUTI (Senza Note)": "#e74c3c"
                    }
                )
                fig_bar_qual.update_layout(
                    showlegend=False,
                    height=250,
                    margin=dict(t=10, l=10, r=10, b=10),
                    xaxis_title="",
                    yaxis_title=""
                )
                st.plotly_chart(fig_bar_qual, use_container_width=True)
        
            with col_grafico:

                fig_pie_qual = px.pie(
                    stats_qualita, 
                    values='Conteggio', 
                    names='Stato Nota', 
                    hole=0.4,
                    color='Stato Nota',
                    color_discrete_map={
                        "UTILI (Con Note)": "#2ecc71", 
                        "MUTI (Senza Note)": "#e74c3c"
                    }
                )
                fig_pie_qual.update_traces(textinfo='percent+label')
                fig_pie_qual.update_layout(
                    margin=dict(t=30, l=10, r=10, b=10),
                    height=400,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_pie_qual, use_container_width=True)


            # --- ANALISI EVENTI MUTI (Senza Note) ---

            # 1. Lista completa di tutti i commerciali che hanno caricato qualcosa
            TOTALE_per_utente = df_filtrato['Utente'].value_counts().reset_index()
            TOTALE_per_utente.columns = ['Utente', 'TOTALE Eventi']
            
            # 2. Filtriamo gli eventi senza note
            df_muti = df_filtrato[
                df_filtrato['Note'].isnull() | (df_filtrato['Note'].str.strip() == "")
            ].copy()
            
            # 3. Conteggio eventi muti per utente
            stats_muti_raw = df_muti['Utente'].value_counts().reset_index()
            stats_muti_raw.columns = ['Utente', 'N. Eventi Muti']
            
            # 4. UNIONE: Partiamo da tutti i commerciali e aggiungiamo i muti (chi non ne ha avrà NaN)
            stats_muti = TOTALE_per_utente.merge(stats_muti_raw, on='Utente', how='left')
            
            # 5. Pulizia: trasformiamo i NaN in 0 e calcoliamo la percentuale
            stats_muti['N. Eventi Muti'] = stats_muti['N. Eventi Muti'].fillna(0).astype(int)
            stats_muti['Percentuale'] = (stats_muti['N. Eventi Muti'] / stats_muti['TOTALE Eventi'] * 100).round(1)
            
            # Ordiniamo: chi ha più errori in alto, chi ne ha zero in basso
            stats_muti = stats_muti.sort_values('N. Eventi Muti', ascending=True)
            
            # --- LAYOUT ---
            col_grafico, col_vuota = st.columns([5, 3])
            
            with col_grafico: 
                fig_muti = px.bar(
                    stats_muti,
                    x='N. Eventi Muti',
                    y='Utente',
                    orientation='h',
                    title="Incidenza Attività senza descrizione (%)",
                    color_discrete_sequence=['#EF553B'], 
                    text=stats_muti['Percentuale'].apply(lambda x: f'{x}%'),
                    labels={'N. Eventi Muti': 'N. Eventi Muti'}
                )
            
                fig_muti.update_traces(
                    textposition='outside',
                    cliponaxis=False
                )
            
                fig_muti.update_layout(
                    height=350 + (len(stats_muti) * 20), 
                    margin=dict(t=50, l=10, r=50, b=10),
                    xaxis_title="Quota eventi MUTI sul TOTALE personale",
                    yaxis_title=None,
                    showlegend=False
                )
            
                st.plotly_chart(fig_muti, use_container_width=True)
           

            
            # --- ANALISI ESAUSTIVITÀ (Conteggio Parole) ---
            st.divider()
            st.write("### Analisi Esaustività")
            st.write("Analisi degli eventi con almeno una parola nelle note")
            st.write("")
            st.info("""
                ⚠️ Note troppo sintentiche sono poco comprensibili
                * *💡 Tip 1:* tenere traccia della lunghezza delle note.
                * *💡 Tip 2:* impostare una formattazione nelle note nel CRM con le 5 W del giornalismo, sarebbe molto utile
                """)
            st.write("")
            
            # Prepariamo i dati calcolando il numero di parole
            df_esaustivita = df_filtrato.copy()
            # Gestiamo i valori nulli e contiamo le parole
            df_esaustivita['Lunghezza Nota'] = df_esaustivita['Note'].apply(
                lambda x: len(str(x).split()) if pd.notnull(x) and str(x).strip() != "" else 0
            )
            
            # Filtriamo solo quelle che hanno almeno una parola per non schiacciare il grafico sugli zeri
            df_note_vere = df_esaustivita[df_esaustivita['Lunghezza Nota'] > 0]
            
            if not df_note_vere.empty:
                # Calcolo metriche medie di esaustività
                parole_medie = df_note_vere['Lunghezza Nota'].mean()
                parole_mediane = df_note_vere['Lunghezza Nota'].median()
                
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    st.metric("Media parole per nota", f"{parole_medie:.1f}")
                with col_e2:
                    st.metric("Mediana parole per nota", f"{parole_mediane:.0f}")
            
                # Istogramma con Box Plot marginale per vedere la distribuzione
                fig_parole = px.histogram(
                    df_note_vere, 
                    x="Lunghezza Nota",
                    marginal="box", # Aggiunge il box plot sopra l'istogramma
                    nbins=30,
                    title="Distribuzione lunghezza note (numero parole)",
                    color_discrete_sequence=['#2ecc71'],
                    labels={'Lunghezza Nota': 'Numero di Parole'},
                    text_auto=True
                )
            
                fig_parole.update_layout(
                    bargap=0.1,
                    xaxis_title="Conteggio Parole",
                    yaxis_title="Frequenza (N. Eventi)",
                    margin=dict(t=50, l=10, r=10, b=10),
                    height=500
                )
                
                st.plotly_chart(fig_parole, use_container_width=True)

                
                # --- DETTAGLIO PER COMMERCIALE ---
                st.write("#### Esaustività media per Commerciale")
                
                # Calcoliamo sia la media (Lunghezza) che il conteggio (Volume Note)
                stats_comm_parole = df_note_vere.groupby('Utente')['Lunghezza Nota'].agg(['mean', 'count']).reset_index()
                stats_comm_parole.columns = ['Utente', 'Media Parole', 'Volume Note']
                
                # Ordiniamo per la media parole (lunghezza barre)
                stats_comm_parole = stats_comm_parole.sort_values('Media Parole', ascending=False)
                
                fig_comm_parole = px.bar(
                    stats_comm_parole,
                    x='Media Parole',
                    y='Utente',
                    orientation='h',
                    text_auto='.1f',
                    color='Volume Note', # <--- IL COLORE ORA INDICA QUANTE NOTE HA SCRITTO
                    color_continuous_scale='Greens',
                    labels={
                        'Media Parole': 'Lunghezza Media (Parole)',
                        'Volume Note': 'N. Note Scritte'
                    },
                    # Aggiungiamo il dettaglio nel tooltip al passaggio del mouse
                    hover_DATA={'Media Parole': True, 'Volume Note': True, 'Utente': True}
                )
                
                fig_comm_parole.update_layout(
                    height=400, 
                    showlegend=True,
                    coloraxis_colorbar=dict(title="N. Note"),
                    margin=dict(t=30, l=10, r=10, b=10)
                )
                
                st.plotly_chart(fig_comm_parole, use_container_width=True)


        # --- SEZIONE HEATMAP ORARIA ---
        st.write("")
        with st.expander("🕒 Heatmap Oraria"):        
            
            # Prepariamo i dati
            df_heat_base = df_filtrato.copy()
            if not df_heat_base.empty:
                df_heat_base['Ora'] = pd.to_datetime(df_heat_base['Ora Evento'], format='%H:%M').dt.hour
                df_heat_base['Giorno'] = pd.to_datetime(df_heat_base['DATA Evento']).dt.day_name()
            
                # 1. CALCOLO LIMITI DINAMICI (AUTO-CROP)
                # Troviamo la prima e l'ultima ora in cui esiste almeno un evento nel set filtrato
                ora_min = int(df_heat_base['Ora'].min())
                ora_max = int(df_heat_base['Ora'].max())
                ore_dinamiche = list(range(ora_min, ora_max + 1))
            
                # Troviamo i giorni della settimana che hanno almeno un evento
                giorni_ORDINE_std = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                giorni_presenti = [g for g in giorni_ORDINE_std if g in df_heat_base['Giorno'].unique()]
                
                traduzione_giorni = {
                    'Monday': 'Lunedì', 'Tuesday': 'Martedì', 'Wednesday': 'Mercoledì', 
                    'Thursday': 'Giovedì', 'Friday': 'Venerdì', 'Saturday': 'Sabato', 'Sunday': 'Domenica'
                }
            
                # 2. FUNZIONE DI GENERAZIONE CON FRAME DINAMICO FISSO
                def genera_heatmap_crop(df_input, altezza=450):
                    # Raggruppamento
                    h_DATA = df_input.groupby(['Giorno', 'Ora']).size().reset_index(name='Conteggio')
                    
                    # Pivot
                    pivot = h_DATA.pivot(index='Giorno', columns='Ora', values='Conteggio').fillna(0)
                    
                    # FORZATURA LAYOUT SUI LIMITI DINAMICI CALCOLATI PRIMA
                    # Questo garantisce che anche se una specifica attività non ha dati in certe ore/giorni,
                    # il grafico avrà lo stesso identico frame di quello globale
                    pivot = pivot.reindex(index=giorni_presenti, columns=ore_dinamiche, fill_value=0)
                    
                    # Traduzione nomi giorni
                    pivot.index = [traduzione_giorni[g] for g in pivot.index]
                    
                    fig = px.imshow(
                        pivot,
                        labels=dict(x="Ora", y="Giorno", color="Attività"),
                        x=pivot.columns,
                        y=pivot.index,
                        color_continuous_scale='Viridis',
                        text_auto=True,
                        aspect="auto"
                    )
                    fig.update_layout(
                        height=altezza, 
                        margin=dict(l=20, r=20, t=30, b=20),
                        xaxis=dict(tickmode='array', tickvals=ore_dinamiche)
                    )
                    return fig
            
                # 3. VISUALIZZAZIONE
                st.write(f"#### 🌍 Distribuzione Oraria Globale delle Attività")
                st.write(f"Range orario trovato: {ora_min}:00 - {ora_max}:00")
                st.plotly_chart(genera_heatmap_crop(df_heat_base), use_container_width=True)
            
                st.write("---")
                st.write("#### 🔍 Dettaglio per Singola Attività")
            
                lista_attivita = sorted(df_heat_base['Tipo Evento'].unique())
            
                for attivita in lista_attivita:
                    df_tipo = df_heat_base[df_heat_base['Tipo Evento'] == attivita]
                    with st.expander(f"Dettaglio: {attivita}"):
                        # Usiamo la stessa funzione: il layout sarà identico a quella globale
                        st.plotly_chart(genera_heatmap_crop(df_tipo, altezza=400), use_container_width=True)
            else:
                st.warning("Nessun dato disponibile per generare le heatmap nel periodo selezionato.")


    # --- SEZIONE COINVOLGIMENTO MEDIO ---
    st.write("")
    with st.expander("📊 Distribuzione Coinvolgimento"):
        st.write("#### Analisi della Densità di Attività per Azienda")
        
        # 1. Calcolo frequenze
        frequenza_aziende = df_filtrato['Ragione Sociale'].value_counts().reset_index()
        frequenza_aziende.columns = ['Azienda', 'Conteggio']
        
        # 2. Metriche
        media_attivita = frequenza_aziende['Conteggio'].mean()
        mediana_attivita = frequenza_aziende['Conteggio'].median()
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Media Attività/Azienda", f"{media_attivita:.1f}")
        with col_stat2:
            st.metric("Mediana (Punto Centrale)", f"{mediana_attivita:.0f}")
        with col_stat3:
            st.metric("Max Attività su 1 Azienda", frequenza_aziende['Conteggio'].max())
    
        # 3. Grafico combinato: Istogramma + Box Plot marginale
        fig_dist = px.histogram(
            frequenza_aziende, 
            x="Conteggio",
            marginal="box",
            title="Distribuzione Coinvolgimento (Istogramma + Box Plot)",
            labels={'Conteggio': 'N. Attività Ricevute', 'count': 'N. Aziende'},
            color_discrete_sequence=['#3498db'],
            text_auto=True
        )
        
        # --- FIX: Applichiamo xbins SOLO alla traccia dell'istogramma ---
        fig_dist.update_traces(
            xbins=dict(
                start=0.5,
                end=frequenza_aziende['Conteggio'].max() + 0.5,
                size=1
            ),
            selector=dict(type='histogram') # <--- Fondamentale: ignora il box plot
        )
        
        fig_dist.update_layout(
            bargap=0, 
            xaxis_title="Numero di Attività per singola Azienda",
            yaxis_title="Quantità di Aziende",
            margin=dict(t=50, l=10, r=10, b=10),
            height=550,
            xaxis = dict(
                tickmode = 'linear',
                tick0 = 1,
                dtick = 1
            )
        )
        
        st.plotly_chart(fig_dist, use_container_width=True)



    # --- SEZIONE AZIENDE PIÙ COINVOLTE ---
    st.write("")
    with st.expander("🏢 Analisi Coinvolgimento Aziende"):
        st.write("#### Top Aziende per Commerciale")
            
        # 1. Preparazione dati per il Treemap
        # Troviamo per ogni azienda chi è il commerciale che ha fatto più attività
        df_top_comm = df_filtrato.groupby(['Ragione Sociale', 'Utente']).size().reset_index(name='Conteggio')
        
        # Per ogni azienda, prendiamo solo la riga del commerciale con il conteggio massimo
        df_color = df_top_comm.sort_values('Conteggio', ascending=False).drop_duplicates('Ragione Sociale')
        df_color = df_color[['Ragione Sociale', 'Utente']]
        df_color.columns = ['Azienda', 'Commerciale Prevalente']
    
        # 2. Uniamo con i totali per azienda
        stats_aziende = df_filtrato['Ragione Sociale'].value_counts().reset_index()
        stats_aziende.columns = ['Azienda', 'Numero Attività']
        
        df_tree = pd.merge(stats_aziende.head(50), df_color, on='Azienda')
    
        # --- CREAZIONE TREEMAP CON SFUMATURE ---
        fig_tree = px.treemap(
            df_tree, 
            path=['Commerciale Prevalente', 'Azienda'], 
            values='Numero Attività',
            color='Numero Attività', # Cambiamo il target del colore sul valore numerico
            color_continuous_scale='Blues', # O 'Viridis', 'GnBu', etc.
            height=700
        )
        
        # FORZIAMO IL TESTO (Il tuo setup preferito)
        fig_tree.update_traces(
            textinfo="label+value",
            texttemplate="<b>%{label}</b><br>Attività: %{value}",
            hovertemplate="<b>%{label}</b><br>TOTALE: %{value}",
            insidetextfont=dict(size=15),
            textposition="middle center"
        )
        
        # SPOSTAMENTO DELLA BARRA COLORI IN ALTO (Orizzontale)
        fig_tree.update_layout(
            margin=dict(t=80, l=10, r=10, b=10), # Aumentiamo il margine superiore (t=80)
            coloraxis_colorbar=dict(
                title="Intensità Attività",
                thicknessmode="pixels", thickness=15, # Spessore della barra
                lenmode="fraction", len=0.5,           # Lunghezza (50% della larghezza grafico)
                yanchor="top", y=1.1,                  # Posizione verticale (sopra il grafico)
                xanchor="center", x=0.5,               # Centrata orizzontalmente
                orientation="h"                        # ORIENTAMENTO ORIZZONTALE
            )
        )
        
        st.plotly_chart(fig_tree, use_container_width=True)


    
        # --- TABELLA DETTAGLIATA (Quella di prima, con l'aggiunta della pivot) ---
        st.write("#### Dettaglio Attività per Azienda")
        
        pivot_aziende = df_filtrato.pivot_table(
            index='Ragione Sociale', 
            columns='Tipo Evento', 
            values='Utente', 
            aggfunc='count', 
            fill_value=0
        ).reset_index()
    
        colonne_attivita = [c for c in pivot_aziende.columns if c != 'Ragione Sociale']
        pivot_aziende['TOTALE'] = pivot_aziende[colonne_attivita].sum(axis=1)
    
        comm_riferimento = df_filtrato.groupby('Ragione Sociale')['Utente'].unique().apply(lambda x: ", ".join(x)).reset_index()
        comm_riferimento.columns = ['Ragione Sociale', 'Commerciali']
    
        df_finale_aziende = pd.merge(pivot_aziende, comm_riferimento, on='Ragione Sociale')
        cols = ['Ragione Sociale', 'TOTALE'] + list(colonne_attivita) + ['Commerciali']
        df_finale_aziende = df_finale_aziende[cols].sort_values(by='TOTALE', ascending=False)
    
        st.DATAframe(df_finale_aziende, hide_index=True, use_container_width=True)

        
        
        # 1. Preparazione dei dati
        stats = df_filtrato['Utente'].value_counts().reset_index()
        stats.columns = ['Utente', 'Numero Attività']
        
        # Ordiniamo per far apparire il più alto in alto
        stats = stats.sort_values(by='Numero Attività', ascending=True)
    
        # 2. Calcolo della Mediana
        valore_mediana = stats['Numero Attività'].median()
    
        # 3. Creazione Grafico con Plotly (BARRE ORIZZONTALI)
        fig = px.bar(
            stats, 
            x='Numero Attività',      # Crescita verso DESTRA
            y='Utente',              # Commerciali in verticale
            orientation='h',         # Forza l'orientamento orizzontale
            text='Numero Attività',   # Mostra il numero sulla barra
            color='Numero Attività', # Opzionale: colore variabile
            color_continuous_scale='Blues'
        )
    
        # 4. AGGIUNTA RETTA PER LA MEDIANA
        fig.add_vline(
            x=valore_mediana, 
            line_dash="dash", 
            line_color="red",
           annotation_text=f"Mediana: {valore_mediana}", 
            annotation_position="top right"
        )
    
        # Miglioramento layout
        fig.update_layout(
            xaxis_title="Numero di Attività Svolte",
            yaxis_title="Commerciale",
            showlegend=False,
            height=500
        )
    
        # Visualizzazione
        st.plotly_chart(fig, use_container_width=True)
    
        # Visualizzazione metrica rapida
        st.metric("Mediana del Team", f"{valore_mediana} attività")
    
        
        
        # 5. TABELLA (basata su df_filtrato)
        st.write(f"### Dettaglio eventi ({len(df_filtrato)} record)")
        
        # Aggiungiamo 'Note' alla lista delle colonne da visualizzare
        col_view = ['Utente', 'DATA Evento', 'Ora Evento', 'Tipo Evento', 'Ragione Sociale', 'Note']
        
        # Verifichiamo quali colonne sono effettivamente presenti nel file per evitare errori
        col_presenti = [c for c in col_view if c in df_filtrato.columns]
        
        st.DATAframe(
            df_filtrato[col_presenti].sort_values(by=['DATA Evento', 'Ora Evento'], ascending=False),
            use_container_width=True
        )
