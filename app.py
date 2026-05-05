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

        # 4. Gestione specifica della Data
        df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce')
        righe_nulle = df['DATA'].isna().sum()
        df = df.dropna(subset=['DATA'])
        
        if righe_nulle > 0:
            st.warning(f"⚠️ Rimosse {righe_nulle} righe con data non valida.")

        return df

    except Exception as e:
        st.error(f"Errore critico caricamento: {e}")
        return None


def data_range(df):
    
    date = df['DATA'].dropna()
    
    if not date.empty:
        d_min, d_max = date.min().date(), date.max().date()
        #st.info(f"📅 Dati disponibili: dal **{d_min.strftime('%d/%m/%Y')}** al **{d_max.strftime('%d/%m/%Y')}**")
        
        return d_min, d_max
        
    return None, None


def data_filtering(period, df):
    
    if isinstance(period, tuple) and len(period) == 2:
        #data_start, data_end = period
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
        st.error("Dataframe assente o vuoto!")
        return None, None

    # Creiamo una copia per evitare modifiche al dataframe originale
    df = df.copy()

    # --- 1. PULIZIA E CALCOLO DEL TOTALE ---
    # Funzione aggiornata per trattare migliaia (.) e decimali (,)
    def converti_valore(val):
        try:
            if pd.isna(val): return 0.0
            
            # Trasformiamo in stringa e puliamo gli spazi
            val_str = str(val).strip().replace(' ', '')
            
            # GESTIONE FORMATO EUROPEO:
            # 1. Rimuoviamo il punto delle migliaia (es: 1.250,50 -> 1250,50)
            # 2. Sostituiamo la virgola con il punto per i decimali (es: 1250,50 -> 1250.50)
            pulito = val_str.replace('.', '').replace(',', '.')
            
            # Estrae solo numeri, punto decimale e segno meno
            pulito = re.sub(r'[^0-9.-]', '', pulito)
            
            return float(pulito) if pulito else 0.0
        except:
            return 0.0

    # Applichiamo la pulizia alle colonne numeriche necessarie
    for col in ['QT', 'PREZZO', 'IVA']:
        if col in df.columns:
            df[f'{col}_pulito'] = df[col].apply(converti_valore)
        else:
            df[f'{col}_pulito'] = 0.0

    # Calcolo del Totale: (Prezzo * Quantità) + IVA (%)
    # Formula: (P * Q) * (1 + IVA/100)
    df['Totale_TMP'] = (df['PREZZO_pulito'] * df['QT_pulito']) * (1 + (df['IVA_pulito'] / 100))

    # --- 2. VALIDAZIONE TIPO DOC ---
    tipi_ammessi = ["PREVENTIVO", "ORDINE APERTO", "ORDINE"]
    mask_tipo_errato = ~df['TIPOLOGIA DOC.'].astype(str).isin(tipi_ammessi)

    # --- 3. CREAZIONE MASCHERE FINALI ---
    mask_errori = (df['Totale_TMP'] <= 0) | (df['Totale_TMP'].isna()) | mask_tipo_errato

    df_errori = df[mask_errori].copy()
    df_pulito = df[~mask_errori].copy()
    
    # Assegniamo il valore calcolato alla colonna definitiva 'Totale'
    df_pulito['TOTALE'] = df_pulito['Totale_TMP']
    
    # --- 4. PULIZIA FINALE ---
    cols_da_rimuovere = ['QT_pulito', 'PREZZO_pulito', 'IVA_pulito', 'Totale_TMP']
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
    

def render_grafico_torta(data, values_col, names_col, titolo, tipo="numerico"):
    """
    Renderizza un grafico a torta con stile fisso e ordine orario costante.
    """
    
    # Palette Pastello
    palette = {
        "PREVENTIVO": "#A2D2FF",  
        "ORDINE APERTO": "#B4E197", 
        "ORDINE": "#4E944F"         
    }

    # Ordine desiderato in senso orario
    ordine_fisso = ["PREVENTIVO", "ORDINE APERTO", "ORDINE"]

    fig = px.pie(
        data, 
        values=values_col, 
        names=names_col,
        title=titolo,
        hole=0.4,
        color=names_col,
        color_discrete_map=palette,
        category_orders={names_col: ordine_fisso} 
    )

    if tipo == "soldi":
        testo_etichette = '%{label}<br>%{percent}<br>€%{value:,.2f}'
    else:
        testo_etichette = '%{label}<br>%{percent}<br>N. %{value}'

    fig.update_traces(
        textinfo='percent+value+label',
        texttemplate=testo_etichette,
        pull=[0.05] * len(data),
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

    # Creiamo la stringa data PRIMA di ogni altra operazione
    if 'DATA' in df_plot.columns:
        # Convertiamo in datetime se non lo è, poi in stringa
        df_plot['Data_Str'] = pd.to_datetime(df_plot['DATA']).dt.strftime('%d/%m/%Y')
    else:
        df_plot['Data_Str'] = "N.D."

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
        
        # Filtriamo il dataframe per lo stadio attuale
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
                customdata=df_stadio[['Data_Str', 'ID DOCUMENTO', 'CLIENTE', 'TITOLO', 'CODICE GESTIONALE UTENTE']],
                # Definiamo cosa appare al passaggio del mouse
                hovertemplate=(
                    "<b>Totale Articoli:</b> €%{x:,.2f}<br>" +
                    "<b>Data:</b> %{customdata[0]}<br>" +
                    "<b>ID:</b> %{customdata[1]}<br>" +
                    "<b>Cliente:</b> %{customdata[2]}<br>" +
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
    fig.update_xaxes(title_text="Importo Documento (totale articoli) (€)", row=2, col=1)
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
    
    # ** SEPARAZIONE DATAFRAME **
    # Separa il dataframe df in due per Preventivi e Ordini (Aperti e Chiusi)
    
    preventivi = df[df['Tipo Doc.'] == "Preventivo"].copy()
    ordini     = df[df['Tipo Doc.'].isin(["Ordine", "Ordine Aperto"])].copy()

    if preventivi.empty:
        st.warning("⚠️ Nessun preventivo trovato per l'analisi!")
        return

    data_riferimento = df['Data'].max()

    
    # ** Matching per identificare i preventivi aggiudicati **
    # 
    # Cerchiamo i match tra i dataframe di preventivi e ordini, 
    # basandosi sul nome del Cliente e l'Articolo venduto
    # e senza considerare finestre di tempo. 
    # Crea un nuovo dataframe "merged_full" con i match.
    # 
    # Struttura di "merged_full": 
    #     se il Cliente X ha 3 preventivi per l'Oggetto Y 
    #     e ha fatto 2 ordini per l'Oggetto Y, "merged_full"
    #     conterrà 6 righe (tutte le combinazioni possibili).
    #     Poi aggiunge la colonna "diff_giorni" che è la differenza
    #     tra la data dell'ordine e quella del preventivo per ogni 
    #     combinazione possibile. 
    #     Ammette anche differenze negative (Es: ordine 1 Maggio
    #     e preventivo 5 Maggio, diff_giorni = -4). 
    #     Mantenere tutte le combinazioni e ammettere diff_giorni 
    #     negative serve per identificare eventuali anomalie.
    
    merged_full = pd.merge(
        preventivi, 
        ordini, 
        on=['Cliente', 'Oggetto'], 
        suffixes=('_prev', '_ord')
    )
    merged_full['diff_giorni'] = (merged_full['Data_ord'] - merged_full['Data_prev']).dt.days

    
    # ** ORDINI TRACCIABILI **
    # 
    # Diff_giorni viene usata per verificare gli ordini "tracciabili",
    # ovvero ordini di cui è presente un preventivo nel dataset 
    # antecedente all'ordine. 
    # Di tutte le combinazioni vengono conservate quelle dove l'ordine 
    # è avvenuto lo stesso giorno (o dopo) il preventivo. 
    # Di queste ne viene mantenuta una e droppate le altre.
    # A questo stadio non stiamo ancora dicendo che "l'ordine X appartiene 
    # al preventivo Y", ma stiamo verificando che "l'ordine X ha almeno 
    # un padre nel database, quindi non è un orfano
    
    ordini_matchati_totali = merged_full[merged_full['diff_giorni'] >= 0][['Cliente', 'Oggetto', 'Data_ord']].drop_duplicates()

    
    # ** ANALISI ANOMALIE **
    
    # A. ORDINI ORFANI
    # 
    #     L'obiettivo è isolare gli ordini che non hanno alcun preventivo associato nel dataset.
    #     1. Il Merge (how='left'):
    #         - Prende la tabella di tutti gli ordini (dataframe 'ordini').
    #         - Tenta di affiancare gli 'ordini_matchati_totali' per Cliente e Oggetto.
    #         - how='left': se non trova match, i campi della tabella destra saranno riempiti con NaN.
    #         - indicator=True: Crea la colonna '_merge' che funge da 'verdetto':
    #         - 'both': l'ordine ha un preventivo (è tracciabile).
    #         - 'left_only': l'ordine non ha trovato corrispondenze (è un orfano).
    #     2. Il Filtro (.query):
    #         - Seleziona solo le righe marcate come 'left_only', isolando gli ordini 
    #           che non hanno un'offerta commerciale alle spalle.
    #     3. La Pulizia (.drop):
    #         - Rimuove la colonna tecnica '_merge' per restituire un DataFrame pulito
    
    ordini_orfani = ordini.merge(
        ordini_matchati_totali, on=['Cliente', 'Oggetto'], how='left', indicator=True
    ).query('_merge == "left_only"').drop(columns='_merge')


    # B. PREVENTIVI CON ORDINI MULTIPLI
    #     
    #     L'obiettivo è identificare i preventivi che hanno generato più di un ordine 
    #     all'interno della finestra temporale di validità.
    #     1. Definizione dei match validi (valid_matches):
    #         - Filtra il dataframe 'merged_full' per tenere solo le combinazioni 
    #           cronologicamente corrette (diff_giorni >= 0) e che rientrano 
    #           nella 'finestra' di giorni stabilita.
    #     2. Conteggio degli ordini per preventivo (groupby):
    #         - Raggruppa i dati per l'identità univoca del preventivo: 
    #           Cliente, Oggetto (Articolo) e Data del preventivo.
    #         - .size(): Conta quante volte ogni preventivo appare nel set dei match validi.
    #         - .reset_index(name='n_ordini'): Trasforma il risultato in un DataFrame 
    #           nominando 'n_ordini' la colonna con il numero di occorrenze trovate.
    #     3. Filtro Anomalie (counts > 1):
    #         - Isola solo i casi in cui 'n_ordini' è maggiore di 1. 
    #         - Questi sono i preventivi "prolifici" che hanno agganciato più ordini 
    #           o che presentano potenziali duplicati nel sistema gestionale.

    valid_matches         = merged_full[(merged_full['diff_giorni'] >= 0) & (merged_full['diff_giorni'] <= finestra)]
    counts                = valid_matches.groupby(['Cliente', 'Oggetto', 'Data_prev']).size().reset_index(name='n_ordini')
    preventivi_multipli   = counts[counts['n_ordini'] > 1]

    
    # C. ORDINI FUORI TEMPO
    #     
    #     L'obiettivo è isolare gli ordini che hanno un preventivo "padre", ma sono arrivati
    #     oltre il limite di giorni (finestra) stabilito per l'analisi.
    #     1. Filtro Temporale (> finestra):
    #         - Estrae dal dataframe 'merged_full' tutte le combinazioni in cui l'ordine
    #           è avvenuto dopo la scadenza della validità del preventivo.
    #         - .copy(): Crea una copia autonoma del dataframe per le successive manipolazioni.
    #     2. Ordinamento Cronologico (sort_values):
    #         - Ordina i match per 'diff_giorni' in modo crescente. Questo mette in cima 
    #           il match più "vicino" alla scadenza della finestra (il primo preventivo utile).
    #     3. Pulizia dei Duplicati (drop_duplicates):
    #         - Poiché un ordine potrebbe avere più preventivi vecchi alle spalle, 
    #           usiamo 'subset' su Cliente, Oggetto e Data dell'ordine per assicurarci 
    #           che ogni ordine ritardatario compaia una sola volta nella lista.
    #         - Questo evita di sovrastimare l'anomalia se ci sono stati molti preventivi 
    #           tutti scaduti per lo stesso articolo (è stato proposto più volte al 
    #           cliente che non ha mai accettato)
    
    ordini_fuori_tempo = merged_full[merged_full['diff_giorni'] > finestra].copy()
    ordini_fuori_tempo = ordini_fuori_tempo.sort_values('diff_giorni').drop_duplicates(subset=['Cliente', 'Oggetto', 'Data_ord'])

    
    # D. CHECK INTEGRITA (Stesso giorno/cliente/articolo)
    #     
    #     L'obiettivo è individuare se esistono più ordini distinti per lo stesso Cliente 
    #     e lo stesso Articolo avvenuti nella medesima Data. Poiché l'analisi usa la 
    #     Data come chiave temporale, questi casi verrebbero accorpati.
    #     1. Raggruppamento sul dataframe originale (groupby):
    #         - Si raggruppa il dataframe "ordini" per Cliente, Oggetto e Data, 
    #           ovvero i parametri usati per identificare un evento di vendita.
    #         - .size(): Conta quante righe effettive esistono per ogni combinazione.
    #         - .reset_index(name='n_righe'): Crea una tabella riassuntiva con il 
    #           conteggio delle transazioni per ogni triade (Chi, Cosa, Quando).
    #     2. Identificazione dei casi critici (n_righe > 1):
    #         - Filtra solo le combinazioni che compaiono più di una volta nello stesso giorno.
    #         - Questi 'casi_critici' rappresentano ordini che il sistema "appiattirà" 
    #           in un unico match, causando una potenziale sottostima nel conteggio (N.) 
    #           dei documenti vinti, anche se il valore economico totale (Somma €) 
    #           rimarrà corretto.
    
    check_integrita = ordini.groupby(['Cliente', 'Oggetto', 'Data']).size().reset_index(name='n_righe')
    casi_critici = check_integrita[check_integrita['n_righe'] > 1]

    
    
    # ** PREVENTIVI AGGIUDICATI EFFETTIVI **
    # In questa fase avviene la "scelta" definitiva: per ogni preventivo, identifichiamo 
    # quale ordine lo ha effettivamente chiuso, applicando criteri di priorità cronologica.
    # 
    # 1. Ordinamento per Prossimità Temporale (.sort_values):
    #     - Viene ordinato il dataframe 'valid_matches' in base a 'diff_giorni' (dal valore minore al maggiore).
    #     - Questo garantisce che, per ogni preventivo, l'ordine avvenuto più a ridosso 
    #       della data dell'offerta finisca in cima alla lista.
    # 
    # 2. Selezione dell'Ordine "Vincitore" (.drop_duplicates):
    #     - subset=['Cliente', 'Oggetto', 'Data_prev']: Il sistema isola ogni singolo preventivo 
    #       univoco (chi, cosa, quando è stata fatta l'offerta).
    #     - Poiché Pandas, durante il 'drop_duplicates', mantiene solo la PRIMA riga che incontra 
    #       e scarta le successive, e dato che abbiamo ordinato per giorni crescenti, 
    #       verrà conservato solo l'ordine più vicino nel tempo.
    # 
    # 3. Risultato:
    #     - Il dataframe 'vinti_effettivi' conterrà una riga per ogni preventivo trasformato 
    #       in vendita, collegato esclusivamente al suo primo ordine cronologico. 
    #       Tutte le altre combinazioni (es. secondi o terzi ordini dello stesso cliente) 
    #       vengono rimosse per non duplicare le statistiche di conversione.
    
    vinti_effettivi = valid_matches.sort_values('diff_giorni').drop_duplicates(subset=['Cliente', 'Oggetto', 'Data_prev'])

    def calcola_riga_stato(row):
        match = vinti_effettivi[
            (vinti_effettivi['Cliente'] == row['Cliente']) & 
            (vinti_effettivi['Oggetto'] == row['Oggetto']) & 
            (vinti_effettivi['Data_prev'] == row['Data'])
        ]
        if not match.empty:
            tipo_ordine = match.iloc[0]['Tipo Doc._ord']
            durata      = match.iloc[0]['diff_giorni']
            return pd.Series(["Ordini Chiusi" if tipo_ordine == "Ordine" else "Ordini Aperti", durata])

        giorni_passati     = (data_riferimento - row['Data']).days
        giorni_rimanenti   = finestra - giorni_passati
        if giorni_rimanenti < 0: return pd.Series(["Persi", giorni_passati])
        elif giorni_rimanenti <= giorni_scadenza: return pd.Series(["In Scadenza", giorni_passati])
        else: return pd.Series(["In Attesa", giorni_passati])

    preventivi[['Stato', 'Durata']] = preventivi.apply(calcola_riga_stato, axis=1)
    preventivi['Stato_Torta'] = preventivi['Stato'].replace({"Ordini Chiusi": "Aggiudicati", "Ordini Aperti": "Aggiudicati"})

    # --- ETICHETTATURA INTEGRITÀ PREVENTIVI ---
    # Inizializziamo tutti i preventivi come "OK"
    preventivi['Analisi_Integrita'] = "OK"

    # 1. Identifica i preventivi che hanno generato anomalie multiple
    chiavi_multiple = set(preventivi_multipli.apply(lambda x: f"{x['Cliente']}|{x['Oggetto']}|{x['Data_prev']}", axis=1))
    
    # 2. Identifica i preventivi che hanno ordini fuori tempo
    chiavi_fuori_tempo = set(ordini_fuori_tempo.apply(lambda x: f"{x['Cliente']}|{x['Oggetto']}|{x['Data_prev']}", axis=1))

    # 3. Identifica i casi critici (integrità date/accorpamenti)
    chiavi_critiche = set(casi_critici.apply(lambda x: f"{x['Cliente']}|{x['Oggetto']}|{x['Data']}", axis=1))

    def verifica_riga(row):
        chiave = f"{row['Cliente']}|{row['Oggetto']}|{row['Data']}"
        if chiave in chiavi_multiple:
            return "Anomalia: Ordini Multipli"
        if chiave in chiavi_fuori_tempo:
            return "Anomalia: Chiuso Fuori Finestra"
        if chiave in chiavi_critiche:
            return "Anomalia: Dato Duplicato"
        return "Dato Integro"

    preventivi['Analisi_Integrita'] = preventivi.apply(verifica_riga, axis=1)

    # --- GESTIONE ORDINI ORFANI PER REPORT FINALE ---
    ordini_orfani['Stato'] = "Vendita Diretta (Orfano)"
    ordini_orfani['Analisi_Integrita'] = "Anomalia: Ordine Orfano"
    ordini_orfani['Stato_Torta'] = "Aggiudicati"
    
    # Prepariamo il report completo per l'analisi commerciali
    cols_to_keep = ['Data', 'Cliente', 'Oggetto', 'Totale', 'CODICE GESTIONALE UTENTE', 'Stato', 'Analisi_Integrita', 'Stato_Torta']
    report_completo = pd.concat([preventivi, ordini_orfani[cols_to_keep]], ignore_index=True)


    # --- SEZIONE AVVISI ANOMALIE (LAYOUT VERTICALE) ---

    # Verifichiamo se esiste almeno un'anomalia tra le 4 categorie identificate
    if not (preventivi_multipli.empty and ordini_orfani.empty and 
            ordini_fuori_tempo.empty and casi_critici.empty):
        
        st.error("⚠️ Rilevate anomalie nel flusso documenti")
        
        # A. PREVENTIVI MULTIPLI
        if not preventivi_multipli.empty:
            with st.expander(f"🚩 {len(preventivi_multipli)} Preventivi con Ordini Multipli"):
                st.write("Questi preventivi hanno generato più di un ordine (o righe d'ordine distinte) nel periodo di validità.")
                st.dataframe(preventivi_multipli, use_container_width=True, hide_index=True)
    
        # B. ORDINI ORFANI
        if not ordini_orfani.empty:
            with st.expander(f"❓ {len(ordini_orfani)} Ordini Orfani (Senza Preventivo)"):
                st.write("Ordini per i quali non è stato trovato alcun preventivo antecedente nel database.")
                st.dataframe(ordini_orfani[['Data', 'Cliente', 'Oggetto', 'Totale']], use_container_width=True, hide_index=True)
    
        # C. ORDINI FUORI TEMPO
        if not ordini_fuori_tempo.empty:
            with st.expander(f"⏰ {len(ordini_fuori_tempo)} Ordini arrivati Fuori Tempo"):
                df_ft = ordini_fuori_tempo[['Data_ord', 'Cliente', 'Oggetto', 'diff_giorni']].rename(
                    columns={'Data_ord': 'Data Ordine', 'diff_giorni': 'GG dopo Prev.'}
                )
                st.write(f"Ordini che hanno un preventivo nel database, ma sono stati chiusi oltre i {finestra}gg stabiliti.")
                st.dataframe(df_ft, use_container_width=True, hide_index=True)
    
        # D. CASI CRITICI (INTEGRITÀ)
        if not casi_critici.empty:
            with st.expander(f"⚠️ {len(casi_critici)} Casi Critici (Potenziali Accorpamenti)"):
                st.write("Rilevati più ordini per lo stesso cliente/articolo nella medesima data.")
                st.info("Nota tecnica: A causa della mancanza di un ID ordine univoco, questi record vengono conteggiati come singola vendita.")
                st.dataframe(casi_critici, use_container_width=True, hide_index=True)
                
    # --- CALCOLI PER FUNNEL ---
    df_conclusi    = preventivi[preventivi['Stato'].isin(["Ordini Chiusi", "Ordini Aperti", "Persi"])]
    n_conclusi     = len(df_conclusi)
    val_conclusi   = df_conclusi['Totale'].sum()
    n_aperti       = len(preventivi[preventivi['Stato'] == "Ordini Aperti"])
    val_aperti     = preventivi[preventivi['Stato'] == "Ordini Aperti"]['Totale'].sum()
    n_chiusi       = len(preventivi[preventivi['Stato'] == "Ordini Chiusi"])
    val_chiusi     = preventivi[preventivi['Stato'] == "Ordini Chiusi"]['Totale'].sum()

    # --- VISUALIZZAZIONE GRAFICI ---
    st.subheader("📊 Distribuzione Stati Preventivi")
    color_map_torta = {"Aggiudicati": "#4E944F", "In Scadenza": "#FFD700", "In Attesa": "#A2D2FF", "Persi": "#FF9999"}

    r1_c1, r1_c2 = st.columns(2)
    with r1_c1:
        stats_n = preventivi['Stato_Torta'].value_counts().reset_index()
        fig_pie_n = px.pie(stats_n, values='count', names='Stato_Torta', title="Esito (Quantità Totale)", hole=0.4, color='Stato_Torta', color_discrete_map=color_map_torta)
        fig_pie_n.update_layout(legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"))
        st.plotly_chart(fig_pie_n, use_container_width=True)
        
    with r1_c2:
        stats_val = preventivi.groupby('Stato_Torta')['Totale'].sum().reset_index()
        fig_pie_val = px.pie(stats_val, values='Totale', names='Stato_Torta', title="Esito (Valore Totale €)", hole=0.4, color='Stato_Torta', color_discrete_map=color_map_torta)
        fig_pie_val.update_traces(textinfo='percent', hovertemplate='€%{value:,.2f}')
        fig_pie_val.update_layout(legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"))
        st.plotly_chart(fig_pie_val, use_container_width=True)

    r2_c1, r2_c2 = st.columns(2)
    with r2_c1:
        fig_f_n = go.Figure(go.Funnel(
            y=["Preventivi Conclusi", "Ordini Aperti", "Ordini Chiusi"], 
            x=[n_conclusi, n_aperti, n_chiusi],
            textinfo="value+percent initial", 
            marker={"color": ["#D3D3D3", "#B4E197", "#4E944F"]}
        ))
        fig_f_n.update_layout(title="Efficacia Quantità (Casi Chiusi)", height=350)
        st.plotly_chart(fig_f_n, use_container_width=True)
        
    with r2_c2:
        fig_f_v = go.Figure(go.Funnel(
            y=["Volume Concluso", "Ordini Aperti", "Ordini Chiusi"], 
            x=[val_conclusi, val_aperti, val_chiusi],
            textinfo="value+percent initial", 
            marker={"color": ["#D3D3D3", "#B4E197", "#4E944F"]}
        ))
        fig_f_v.update_layout(title="Efficacia Valore (Casi Chiusi)", height=350)
        st.plotly_chart(fig_f_v, use_container_width=True)

    # --- RIEPILOGO METRICHE ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Totale Emesso", f"€ {preventivi['Totale'].sum():,.2f}")
    
    val_vinti_tot = val_aperti + val_chiusi
    n_vinti_tot = n_aperti + n_chiusi
    m2.metric("Vinto (Aperti+Chiusi)", f"€ {val_vinti_tot:,.2f}", f"{n_vinti_tot} Doc")
    
    t_n = (n_vinti_tot / n_conclusi * 100) if n_conclusi > 0 else 0
    t_v = (val_vinti_tot / val_conclusi * 100) if val_conclusi > 0 else 0
    m3.metric("Tasso Conversione Reale", f"{t_n:.1f}%", f"{t_v:.1f}% Valore")
    
    n_scad = len(preventivi[preventivi['Stato'] == "In Scadenza"])
    val_scad = preventivi[preventivi['Stato'] == "In Scadenza"]['Totale'].sum()
    m4.metric("In Scadenza", f"{n_scad} Doc", f"€ {val_scad:,.2f}", delta_color="inverse")

    # --- REGISTRO FINALE ---
    with st.expander("📋 Registro Dettagliato Preventivi", expanded=True):
        df_f = preventivi[['Data', 'Cliente', 'Oggetto', 'Totale', 'Stato', 'Durata']].copy()
        df_f = df_f.rename(columns={'Data': 'Data Preventivo', 'Oggetto': 'Articolo'})
        
        prio = {"In Scadenza": 0, "Ordini Aperti": 1, "Ordini Chiusi": 2, "In Attesa": 3, "Persi": 4}
        df_f['p'] = df_f['Stato'].map(prio)
        df_f = df_f.sort_values(['p', 'Data Preventivo'], ascending=[True, False]).drop(columns='p')
    
        def colora(val):
            if val == 'Ordini Chiusi': return 'color: #4E944F; font-weight: bold'
            if val == 'Ordini Aperti': return 'color: #B4E197; font-weight: bold'
            if val == 'In Scadenza': return 'color: #CCAA00; font-weight: bold' 
            if val == 'Persi': return 'color: #FF9999'
            return 'color: #A2D2FF'
    
        st.dataframe(
            df_f.style.format({
                'Data Preventivo': lambda x: x.strftime('%d/%m/%Y'),
                'Totale': '{:,.2f} €',
                'Durata': '{:.0f} gg'
            }).map(colora, subset=['Stato']),
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
    
    # Filtriamo il dataframe per considerare solo i dati integri nei calcoli di conversione
    df_integro = df_report[df_report['Analisi_Integrita'] == "Dato Integro"].copy()

    # 2. CALCOLO METRICHE AGGREGATE
    # Raggruppiamo per il codice gestionale dell'utente
    performance = df_integro.groupby('CODICE GESTIONALE UTENTE').agg(
        Nr_Preventivi    = ('Totale', 'count'),
        Volume_Offerto   = ('Totale', 'sum'),
        Nr_Vinti         = ('Stato_Torta', lambda x: (x == "Aggiudicati").sum()),
        Volume_Vinto     = ('Totale', lambda x: x[df_integro.loc[x.index, 'Stato_Torta'] == "Aggiudicati"].sum())
    ).reset_index()

    # Calcolo Tassi di Conversione (Hit Rate)
    performance['Conversion_Rate_Nr']  = (performance['Nr_Vinti'] / performance['Nr_Preventivi'] * 100).fillna(0)
    performance['Conversion_Rate_Val'] = (performance['Volume_Vinto'] / performance['Volume_Offerto'] * 100).fillna(0)

    # --- RIORDINAMENTO COLONNE ---
    # Impostiamo l'ordine richiesto: Nr_Preventivi, Nr_Vinti, Nr_Rate, Vol_Preventivi, Vol_Vinto, Vol_Rate
    ordine_colonne = [
        'CODICE GESTIONALE UTENTE', 
        'Nr_Preventivi', 
        'Nr_Vinti', 
        'Nr_Rate', 
        'Vol_Preventivi', 
        'Vol_Vinto', 
        'Vol_Rate'
    ]
    performance = performance[ordine_colonne]

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
        st.dataframe(anomalie_count, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Nessuna anomalia rilevata per i commerciali!")

    # --- Dettaglio Singolo Agente ---
    st.divider()
    agente_sel = st.selectbox("Seleziona un commerciale per il dettaglio righe:", df_report['CODICE GESTIONALE UTENTE'].unique())
    
    if agente_sel:
        df_agente = df_report[df_report['CODICE GESTIONALE UTENTE'] == agente_sel]
        
        col1, col2 = st.columns(2)
        col1.metric("Totale Righe Gestite", len(df_agente))
        col2.metric("Di cui Integre", len(df_agente[df_agente['Analisi_Integrita'] == "Dato Integro"]))
        
        st.dataframe(
            df_agente[['Data', 'Cliente', 'Oggetto', 'Totale', 'Stato', 'Analisi_Integrita']],
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
        date_min, date_max = data_range(df_events)

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
    date_min, date_max = data_range(df_orders)
        

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
        df_events = data_filtering(period, df_events)

    if df_orders is not None:
        df_orders = data_filtering(period, df_orders)
        
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
    # Creaiamo un dataframe suddiviso per l'ID dei documenti.
    # Per ogni ID avremo la tipologia di documento (preventivo, ordine aperto, ordine)
    # e il totale (€) degli articoli per quel documento.
    
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
                    data=conteggio_qty, 
                    values_col='Conteggio', 
                    names_col='TIPOLOGIA DOC.', 
                    titolo="N. Documenti Univoci",
                    tipo="numerico"
                )
            
            with col_destra:
                render_grafico_torta(
                    data=conteggio_vol, 
                    values_col='TOTALE', 
                    names_col='TIPOLOGIA DOC.', 
                    titolo="Valore Economico Totale",
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
        
        # Prezzo Medio per Ordine Completo
        df_riepilogo['Media (€)'] = (df_riepilogo['TOTALE'] / df_riepilogo['Conteggio'])
        
        # Ordinamento e formattazione nomi (TUTTO MAIUSCOLO per le colonne)
        ordine_fisso = ["PREVENTIVO", "ORDINE APERTO", "ORDINE"]
        df_riepilogo['TIPOLOGIA DOC.'] = pd.Categorical(df_riepilogo['TIPOLOGIA DOC.'], categories=ordine_fisso, ordered=True)
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
                help="Giorni massimi per convertire un preventivo in ordine."
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
                totale_attivita = len(df_filtrato)
                st.write("")
                st.metric("Totale Attività", totale_attivita)
                st.dataframe(stats_tipo, hide_index=True, use_container_width=True)

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
            totale_per_utente = df_filtrato['Utente'].value_counts().reset_index()
            totale_per_utente.columns = ['Utente', 'Totale Eventi']
            
            # 2. Filtriamo gli eventi senza note
            df_muti = df_filtrato[
                df_filtrato['Note'].isnull() | (df_filtrato['Note'].str.strip() == "")
            ].copy()
            
            # 3. Conteggio eventi muti per utente
            stats_muti_raw = df_muti['Utente'].value_counts().reset_index()
            stats_muti_raw.columns = ['Utente', 'N. Eventi Muti']
            
            # 4. UNIONE: Partiamo da tutti i commerciali e aggiungiamo i muti (chi non ne ha avrà NaN)
            stats_muti = totale_per_utente.merge(stats_muti_raw, on='Utente', how='left')
            
            # 5. Pulizia: trasformiamo i NaN in 0 e calcoliamo la percentuale
            stats_muti['N. Eventi Muti'] = stats_muti['N. Eventi Muti'].fillna(0).astype(int)
            stats_muti['Percentuale'] = (stats_muti['N. Eventi Muti'] / stats_muti['Totale Eventi'] * 100).round(1)
            
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
                    xaxis_title="Quota eventi MUTI sul totale personale",
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
                    hover_data={'Media Parole': True, 'Volume Note': True, 'Utente': True}
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
                df_heat_base['Giorno'] = pd.to_datetime(df_heat_base['Data Evento']).dt.day_name()
            
                # 1. CALCOLO LIMITI DINAMICI (AUTO-CROP)
                # Troviamo la prima e l'ultima ora in cui esiste almeno un evento nel set filtrato
                ora_min = int(df_heat_base['Ora'].min())
                ora_max = int(df_heat_base['Ora'].max())
                ore_dinamiche = list(range(ora_min, ora_max + 1))
            
                # Troviamo i giorni della settimana che hanno almeno un evento
                giorni_ordine_std = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                giorni_presenti = [g for g in giorni_ordine_std if g in df_heat_base['Giorno'].unique()]
                
                traduzione_giorni = {
                    'Monday': 'Lunedì', 'Tuesday': 'Martedì', 'Wednesday': 'Mercoledì', 
                    'Thursday': 'Giovedì', 'Friday': 'Venerdì', 'Saturday': 'Sabato', 'Sunday': 'Domenica'
                }
            
                # 2. FUNZIONE DI GENERAZIONE CON FRAME DINAMICO FISSO
                def genera_heatmap_crop(df_input, altezza=450):
                    # Raggruppamento
                    h_data = df_input.groupby(['Giorno', 'Ora']).size().reset_index(name='Conteggio')
                    
                    # Pivot
                    pivot = h_data.pivot(index='Giorno', columns='Ora', values='Conteggio').fillna(0)
                    
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
            hovertemplate="<b>%{label}</b><br>Totale: %{value}",
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
        pivot_aziende['Totale'] = pivot_aziende[colonne_attivita].sum(axis=1)
    
        comm_riferimento = df_filtrato.groupby('Ragione Sociale')['Utente'].unique().apply(lambda x: ", ".join(x)).reset_index()
        comm_riferimento.columns = ['Ragione Sociale', 'Commerciali']
    
        df_finale_aziende = pd.merge(pivot_aziende, comm_riferimento, on='Ragione Sociale')
        cols = ['Ragione Sociale', 'Totale'] + list(colonne_attivita) + ['Commerciali']
        df_finale_aziende = df_finale_aziende[cols].sort_values(by='Totale', ascending=False)
    
        st.dataframe(df_finale_aziende, hide_index=True, use_container_width=True)

        
        
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
        col_view = ['Utente', 'Data Evento', 'Ora Evento', 'Tipo Evento', 'Ragione Sociale', 'Note']
        
        # Verifichiamo quali colonne sono effettivamente presenti nel file per evitare errori
        col_presenti = [c for c in col_view if c in df_filtrato.columns]
        
        st.dataframe(
            df_filtrato[col_presenti].sort_values(by=['Data Evento', 'Ora Evento'], ascending=False),
            use_container_width=True
        )
