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
        
        df = pd.read_csv(file, sep=';', encoding='utf-8-sig')
        if df.shape[1] <= 1:
            file.seek(0)
            df = pd.read_csv(file, sep=',', encoding='utf-8-sig')

        # Pulizia colonne
        df.columns = df.columns.str.strip().str.replace('ï»¿', '', regex=False)
        
        righe_iniziali = len(df)
        
        # 2. Gestione Generica della Data
        possibili_nomi_data = ['Data Evento', 'Data']
        colonna_data = next((c for c in possibili_nomi_data if c in df.columns), None)

        if colonna_data:
            # Conversione a datatime
            df[colonna_data] = pd.to_datetime(df[colonna_data], dayfirst=True, errors='coerce')
            
            # Conta quante date non sono valide prima di droppare
            righe_nulle = df[colonna_data].isna().sum()
            
            df = df.rename(columns={colonna_data: 'Data'})
            df = df.dropna(subset=['Data'])
            
            # ALERT se abbiamo perso dati
            if righe_nulle > 0:
                st.warning(f"⚠️ Attenzione: {righe_nulle} righe sono state rimosse perché la data non era valida o era mancante.")
                
         # Se fallisce, mostriamo all'utente cosa ha effettivamente letto Pandas
        else:
            st.error(f"Colonna date non trovata! Colonne rilevate: {list(df.columns)}")
            return None

        # 3. Pulizia Tipo Evento
        if 'Tipo Evento' in df.columns:
            df['Tipo Evento'] = df['Tipo Evento'].apply(
                lambda x: re.sub(r'[^a-zA-Z\s]', '', str(x)).strip().upper() if pd.notnull(x) else x
            )
            
        return df

    except Exception as e:
        st.error(f"Errore critico caricamento: {e}")
        return None


def data_range(df):
    
    date = df['Data'].dropna()
    
    if not date.empty:
        d_min, d_max = date.min().date(), date.max().date()
        st.info(f"📅 Dati disponibili: dal **{d_min.strftime('%d/%m/%Y')}** al **{d_max.strftime('%d/%m/%Y')}**")
        
        return d_min, d_max
        
    return None, None


def data_filtering(period, df):
    
    if isinstance(period, tuple) and len(period) == 2:
        #data_start, data_end = period
        df_filtrato = df[
                (df['Data'].dt.date >= period[0]) & 
                (df['Data'].dt.date <= period[1])
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

    # --- VALIDAZIONE IMPORTI ---
    df['Totale_TMP'] = df['Totale'].astype(str).str.replace(' ', '').str.replace(',', '.')

    def valida_puro(valore_str):
        try:
            pulito = re.sub(r'[^0-9.-]', '', valore_str)
            if not pulito: return None
            num = float(pulito)
            if num > 0:
                return num
            return None
        except:
            return None

    serie_validata = df['Totale_TMP'].apply(valida_puro)
    
    # --- VALIDAZIONE TIPO DOC ---
    # Definiamo le tipologie di articoli validi
    tipi_ammessi = ["Preventivo", "Ordine Aperto", "Ordine"]
    
    # Maschera per Tipo Doc: True se il tipo NON è tra quelli ammessi
    # Nota: usiamo .fillna('') per gestire eventuali celle vuote senza crashare
    mask_tipo_errato = ~df['Tipo Doc.'].astype(str).isin(tipi_ammessi)

    # --- CREAZIONE MASCHERE FINALI ---
    # Un errore è tale se l'importo è nullo, NaN o negativo
    # OPPURE se il Tipo Doc è errato (mask_tipo_errato)
    mask_errori = serie_validata.isna() | mask_tipo_errato

    df_errori = df[mask_errori].copy()
    df_pulito = df[~mask_errori].copy()
    
    # Assegniamo i valori numerici puliti al df_pulito
    df_pulito['Totale'] = serie_validata[~mask_errori]
    
    # Pulizia colonne temporanee
    df_pulito = df_pulito.drop(columns=['Totale_TMP'])
    df_errori = df_errori.drop(columns=['Totale_TMP'])

    # --- DEBUG FORZATO ---
    st.write(f"✅ File caricato: {len(df)} righe totali rilevate.")
    
    if len(df_errori) > 0:
        with st.expander("⚠️ ERRORI RILEVATI", expanded=True):
            st.error(f"Trovate {len(df_errori)} righe scartate (Importo non valido o Tipo Doc non ammesso)!")
            st.dataframe(df_errori)
    else:
        st.success("Nessun errore rilevato (Tutti gli importi e i tipi documento sono validi).")

    return df_pulito, df_errori
    

def render_grafico_torta(data, values_col, names_col, titolo, tipo="numerico"):
    """
    Renderizza un grafico a torta con stile fisso e ordine orario costante.
    """
    
    # Palette Pastello
    colori_personalizzati = {
        "Preventivo": "#A2D2FF",    # Azzurro
        "Ordine Aperto": "#B4E197", # Verde chiaro
        "Ordine": "#4E944F"         # Verde bosco
    }

    # Ordine desiderato in senso orario
    ordine_fisso = ["Preventivo", "Ordine Aperto", "Ordine"]

    fig = px.pie(
        data, 
        values=values_col, 
        names=names_col,
        title=titolo,
        hole=0.4,
        color=names_col,
        color_discrete_map=colori_personalizzati,
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
    if 'Data' in df_plot.columns:
        # Convertiamo in datetime se non lo è, poi in stringa
        df_plot['Data_Str'] = pd.to_datetime(df_plot['Data']).dt.strftime('%d/%m/%Y')
    else:
        df_plot['Data_Str'] = "N.D."

    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.5, 0.5]
    )

    colori = {"Preventivo": "#A2D2FF", "Ordine Aperto": "#B4E197", "Ordine": "#4E944F"}
    stadi = ["Preventivo", "Ordine Aperto", "Ordine"]

    for stadio in stadi:
        
        # Filtriamo il dataframe per lo stadio attuale
        df_stadio = df_plot[df_plot['Tipo Doc.'] == stadio]
        
        if df_stadio.empty: continue

        vals = df_stadio['Totale']

        # ISTOGRAMMA (Row 2)
        fig.add_trace(
            go.Histogram(
                x=vals,
                name=stadio,
                marker_color=colori[stadio],
                opacity=0.6,
                nbinsx=20,
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
                marker_color=colori[stadio],
                boxpoints='all',
                jitter=0.5,       
                pointpos=0,
                legendgroup=stadio,
                showlegend=False,
                orientation='h',
                # Passiamo i dati extra qui
                customdata=df_stadio[['Data_Str', 'Oggetto', 'Cliente', 'Agente']],
                # Definiamo cosa appare al passaggio del mouse
                hovertemplate=(
                    "<b>Importo:</b> €%{x:,.2f}<br>" +
                    "<b>Data:</b> %{customdata[0]}<br>" +
                    "<b>Oggetto:</b> %{customdata[1]}<br>" +
                    "<b>Cliente:</b> %{customdata[2]}<br>" +
                    "<b>Agente:</b> %{customdata[3]}<br>" +
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
    fig.update_xaxes(title_text="Importo Articolo (€)", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)
    



def analisi_conversione_preventivi(df, finestra, giorni_scadenza=7):
    
    # 1. Preparazione Dataframe
    preventivi = df[df['Tipo Doc.'] == "Preventivo"].copy()
    ordini = df[df['Tipo Doc.'].isin(["Ordine", "Ordine Aperto"])].copy()

    if preventivi.empty:
        st.warning("Nessun preventivo trovato.")
        return

    # Data di riferimento (l'ultima data disponibile nel dataset)
    data_riferimento = df['Data'].max()

    # 2. Matching per identificare i "Vinti"
    merged = pd.merge(
        preventivi, 
        ordini, 
        on=['Cliente', 'Oggetto'], 
        suffixes=('_prev', '_ord')
    )
    merged['diff_giorni'] = (merged['Data_ord'] - merged['Data_prev']).dt.days
    
    vinti_effettivi = merged[
        (merged['diff_giorni'] >= 0) & (merged['diff_giorni'] <= finestra)
    ].sort_values('diff_giorni').drop_duplicates(subset=['Cliente', 'Oggetto', 'Data_prev'])

    # 3. Nuova Logica di Stato con "In Scadenza"
    def calcola_riga_stato(row):
        # Cerchiamo se è vinto
        match = vinti_effettivi[
            (vinti_effettivi['Cliente'] == row['Cliente']) & 
            (vinti_effettivi['Oggetto'] == row['Oggetto']) & 
            (vinti_effettivi['Data_prev'] == row['Data'])
        ]
        
        if not match.empty:
            tipo_ordine = match.iloc[0]['Tipo Doc._ord']
            durata = match.iloc[0]['diff_giorni']
            return pd.Series(["Ordine Chiuso" if tipo_ordine == "Ordine" else "Ordine Aperto", durata])
        
        # Se non è vinto, calcoliamo quanto tempo è passato
        giorni_passati = (data_riferimento - row['Data']).days
        giorni_rimanenti = finestra - giorni_passati

        if giorni_rimanenti < 0:
            return pd.Series(["Perso", giorni_passati])
        elif giorni_rimanenti <= giorni_scadenza:
            return pd.Series(["In Scadenza", giorni_passati])
        else:
            return pd.Series(["In Attesa", giorni_passati])

    preventivi[['Stato', 'Durata']] = preventivi.apply(calcola_riga_stato, axis=1)

    # --- GRAFICI ---
    st.subheader("🎯 Dashboard Conversioni e Scadenze")
    col_l, col_r = st.columns(2)
    
    with col_l:
        stats_pie = preventivi['Stato'].value_counts().reset_index()
        fig_pie = px.pie(
            stats_pie, values='count', names='Stato', 
            title="Dettaglio Stati", hole=0.4,
            color='Stato',
            color_discrete_map={
                "Ordine Chiuso": "#4E944F", # Verde
                "Ordine Aperto": "#B4E197", # Verde chiaro
                "In Scadenza": "#FFD700",   # GIALLO GOLD
                "In Attesa": "#A2D2FF",     # Azzurro
                "Perso": "#FF9999"          # Rosso
            }
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_r:
        # Funnel (Emessi -> Accettati -> Chiusi)
        n_tot = len(preventivi)
        n_vinti = len(preventivi[preventivi['Stato'].str.contains("Ordine")])
        n_chiusi = len(preventivi[preventivi['Stato'] == "Ordine Chiuso"])
        
        fig_funnel = go.Figure(go.Funnel(
            y=["Emessi", "Accettati", "Chiusi"],
            x=[n_tot, n_vinti, n_chiusi],
            textinfo="value+percent initial",
            marker={"color": ["#A2D2FF", "#B4E197", "#4E944F"]}
        ))
        st.plotly_chart(fig_funnel, use_container_width=True)

    # --- TABELLA FINALE ---
    st.divider()
    st.write(f"**📋 Registro Preventivi (Finestra: {finestra}gg, Avviso Scadenza: {giorni_scadenza}gg)**")

    df_finale = preventivi[['Data', 'Cliente', 'Oggetto', 'Totale', 'Stato', 'Durata']].copy()
    df_finale = df_finale.rename(columns={'Data': 'Data Preventivo', 'Oggetto': 'Articolo'})
    df_finale = df_finale.sort_values(['Stato', 'Data Preventivo'], ascending=[True, False])

    def colora_stato(val):
        if val in ['Ordine Chiuso', 'Ordine Aperto']: return 'color: #4E944F; font-weight: bold'
        if val == 'In Scadenza': return 'color: #CCAA00; font-weight: bold' # Giallo scuro per leggibilità su bianco
        if val == 'Perso': return 'color: #FF9999'
        return 'color: #A2D2FF'

    st.dataframe(
        df_finale.style.format({
            'Data Preventivo': lambda x: x.strftime('%d/%m/%Y'),
            'Totale': '{:,.2f} €',
            'Durata': '{:.0f} gg'
        }).map(colora_stato, subset=['Stato']),
        use_container_width=True,
        hide_index=True
    )




# ***********************************************************************
#                                 MAIN APP
# ***********************************************************************


st.header("Analisi Commerciali")
st.divider()

# Inizializzazione
df_events = None
df_orders = None
# Limiti filtro date calendario
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
    #  PANORAMICA
    # ************
    
    # Aggregazione quantità e volumi
    conteggio_qty             = df_orders['Tipo Doc.'].value_counts().reset_index()
    conteggio_qty.columns     = ['Tipo Doc.', 'Conteggio'] 
    conteggio_vol             = df_orders.groupby('Tipo Doc.')['Totale'].sum().reset_index()
    
    with st.expander("📊 Panoramica Quantità e Volumi", expanded=True):
        
        if not conteggio_qty.empty and not conteggio_vol.empty:
            
            col_sinistra, col_destra = st.columns(2)
            
            with col_sinistra:
                render_grafico_torta(
                    data=conteggio_qty, 
                    values_col='Conteggio', 
                    names_col='Tipo Doc.', 
                    titolo="Volume per Numero Articoli",
                    tipo="numerico"
                )
            
            with col_destra:
                render_grafico_torta(
                    data=conteggio_vol, 
                    values_col='Totale', 
                    names_col='Tipo Doc.', 
                    titolo="Volume per Valore Economico",
                    tipo="soldi"
                )
        else:
            st.warning("Dati insufficienti per generare i grafici.")

        

        # 1. Mediana
        mediane = df_orders.groupby('Tipo Doc.')['Totale'].median().reset_index()
        mediane.columns = ['Tipo Doc.', 'Mediana (€)']
        
        # 2. Uniamo i dati: Quantità + Volumi + Mediane
        df_riepilogo = pd.merge(conteggio_qty, conteggio_vol, on='Tipo Doc.')
        df_riepilogo = pd.merge(df_riepilogo, mediane, on='Tipo Doc.')
        
        # 3. Calcolo Percentuali sul totale
        tot_qty = df_riepilogo['Conteggio'].sum()
        tot_vol = df_riepilogo['Totale'].sum()
        df_riepilogo['% Qty'] = (df_riepilogo['Conteggio'] / tot_qty * 100).round(1).astype(str) + '%'
        df_riepilogo['% Vol'] = (df_riepilogo['Totale'] / tot_vol * 100).round(1).astype(str) + '%'
        
        # 4. Calcolo Prezzo Medio
        df_riepilogo['Media (€)'] = (df_riepilogo['Totale'] / df_riepilogo['Conteggio'])
        
        # 5. Ordinamento e Selezione Colonne per una lettura logica
        ordine_fisso = ["Preventivo", "Ordine Aperto", "Ordine"]
        df_riepilogo['Tipo Doc.'] = pd.Categorical(df_riepilogo['Tipo Doc.'], categories=ordine_fisso, ordered=True)
        df_riepilogo = df_riepilogo.sort_values('Tipo Doc.')
        
        # 6. Organizziamo le colonne in modo che la tabella sia facile da leggere
        colonne_finali = [
            'Tipo Doc.', 
            'Conteggio', '% Qty',      # Gruppo Quantità
            'Totale', '% Vol',         # Gruppo Valore Economico
            'Media (€)', 'Mediana (€)' # Indicatori di performance
        ]

        # 7. Stampa tabella
        st.write("")
        st.write("")
        st.dataframe(
            df_riepilogo[colonne_finali].style.format({
                'Totale': '€ {:,.2f}',
                'Media (€)': '€ {:,.2f}',
                'Mediana (€)': '€ {:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        st.caption("Nota: La Mediana è spesso più affidabile della Media perché non viene influenzata da singoli ordini eccezionalmente alti o bassi.")

        # Istogramma e BoxPlot della distribuzione articoli
        st.divider()
        st.write("#### Distribuzione Ordini e Preventivi")
        st.info("""
        **Come leggere questo grafico:**
        * **Istogramma:** Indica le fasce di prezzo dove si concentrano i tuoi volumi.
        * **Box Plot:** La linea centrale è la **Mediana**. I punti isolati sono gli **Outliers** (⚠️ ordini eccezionalmente grandi -> verificare).
        """)
        plot_distribuzione_ordini(df_orders)
        
       
    # ***********************
    #  PANORAMICA - ARTICOLI
    # ***********************

    with st.expander("📊 Panoramica Articoli Venduti", expanded=True):

        # Filtriamo gli ordini vinti ("Ordine Aperto" e "Ordine")
        df_ordini_vinti = df_orders[df_orders['Tipo Doc.'].isin(["Ordine Aperto", "Ordine"])].copy()
    
        if not df_ordini_vinti.empty:
            
            # Raggruppamento per articolo venduto
            df_stats = df_ordini_vinti.groupby('Oggetto').agg(
                Ordini=('Oggetto', 'count'),
                Fatturato=('Totale', 'sum'),
                Mediana_Fatturato=('Totale', 'median')
            ).reset_index()
        
            # Calcolo percentuali per la tabella
            tot_n = df_stats['Ordini'].sum()
            tot_val = df_stats['Fatturato'].sum()
            df_stats['% Ordini'] = (df_stats['Ordini'] / tot_n) * 100
            df_stats['% Fatturato'] = (df_stats['Fatturato'] / tot_val) * 100
        
            # --- FUNZIONE INTERNA PER CREARE I TOP 5 + ALTRO ---
            def prepara_top5_con_altro(df, col_valore):
                top5 = df.nlargest(5, col_valore).copy()
                altri_df = df[~df['Oggetto'].isin(top5['Oggetto'])]
                
                if not altri_df.empty:
                    riga_altro = pd.DataFrame({
                        'Oggetto': ['Altro'],
                        'Ordini': [altri_df['Ordini'].sum()],
                        'Fatturato': [altri_df['Fatturato'].sum()]
                    })
                    return pd.concat([top5, riga_altro], ignore_index=True)
                return top5
        
            # Prepariamo i dati per i grafici
            chart_data_count = prepara_top5_con_altro(df_stats, 'Ordini')
            chart_data_revenue = prepara_top5_con_altro(df_stats, 'Fatturato')
        
            # 2. Visualizzazione Grafici
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Top 5 per Numero di Ordini**")
                fig_count = px.pie(chart_data_count, values='Ordini', names='Oggetto', 
                                   hole=0.3, color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig_count, use_container_width=True)
    
            with col2:
                st.write("**Top 5 per Volume d'Affari (€)**")
                fig_rev = px.pie(chart_data_revenue, values='Fatturato', names='Oggetto', 
                                 hole=0.3, color_discrete_sequence=px.colors.sequential.Blues_r)
                st.plotly_chart(fig_rev, use_container_width=True)
        
            # 3. Tabella riassuntiva (rimane con tutti i dettagli, ordinata come richiesto)
            st.divider()
            ordine_colonne = ['Oggetto', 'Ordini', '% Ordini', 'Fatturato', '% Fatturato', 'Mediana_Fatturato']
            df_visualizzazione = df_stats[ordine_colonne].sort_values(by='Fatturato', ascending=False)
            
            st.write("**Dettaglio Completo per Articolo**")
            st.dataframe(
                df_visualizzazione.style.format({
                    'Ordini': '{:,.0f}',
                    '% Ordini': '{:.1f}%',
                    'Fatturato': '{:,.2f} €',
                    '% Fatturato': '{:.1f}%',
                    'Mediana_Fatturato': '{:,.2f} €'
                }),
                use_container_width=True,
                hide_index=True
            )


    with st.expander("Analisi Conversione Preventivi", expanded=True):
        # Creiamo due colonne per i parametri
        c1, c2, c3, c4, c5 = st.columns([0.2, 1, 0.3, 1, 0.2])
        
        with c2:
            finestra = st.slider(
                "Validità preventivi (giorni):", 
                min_value=1, max_value=180, value=30, 
                help="Giorni massimi per convertire un preventivo in ordine."
            )
        
        with c4:
            scadenza = st.number_input(
                "Pre-avviso 'In Scadenza' (giorni):", 
                min_value=1, max_value=30, value=7,
                help="Giorni prima della scadenza per attivare l'avviso GIALLO."
            )
        
        # Chiamata alla funzione aggiornata
        analisi_conversione_preventivi(df_orders, finestra, scadenza)
    
        

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
