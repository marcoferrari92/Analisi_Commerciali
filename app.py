import streamlit as st
import pandas as pd
import plotly.express as px
import re

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
    """
    Analizza la colonna 'Totale'.
    Ritorna:
    - df_pulito: Solo le righe con importi numerici validi (colonna Totale convertita in float).
    - df_errori: Solo le righe con importi errati (stringhe, simboli, formati non validi).
    """
    if df is None or df.empty:
        st.error("Dataframe assente o vuoto!")
        return

    # Funzione rigorosa di validazione
    def valida_puro(valore):
        num = None
        # 1. Conversione se già numerico
        if isinstance(valore, (int, float)) and not pd.isna(valore):
            num = float(valore)
        
        # 2. Conversione se stringa
        elif isinstance(valore, str):
            try:
                num = float(valore)
            except ValueError:
                num = None

        # 3. Controllo positività (SISTEMATO: ora è dentro il flusso)
        if num is not None and num > 0:
            return num
        return None

    # Creiamo una copia per non modificare il DF originale durante l'elaborazione
    temp_df = df.copy()
    
    # Tentiamo la conversione sulla colonna Totale
    temp_df['Totale'] = temp_df['Totale'].apply(valida_puro)

    # Separiamo i due DataFrame
    # 1. Righe con errori (dove Totale è diventato None dopo il tentativo di conversione)
    df_errori = temp_df[temp_df['Totale'].isna()].copy()
    
    # 2. Righe pulite (togliamo i valori nulli)
    df_pulito = temp_df.dropna(subset=['Totale']).copy()

    # Opzionale: Segnalazione visiva in Streamlit se ci sono errori
    if not df_errori.empty:
        with st.expander(f"⚠️ Attenzione: {len(df_errori)} righe scartate", expanded=False):
            st.warning("Queste righe contengono importi non validi e sono state escluse dalle analisi.")
            st.table(df_errori[['Data', 'Oggetto', 'Tipo Doc.', 'Totale']] if 'Totale' in df_errori.columns else df_errori)

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
        title_x=0  # Riportato a 0 per stare a sinistra
    )
    
    st.plotly_chart(fig, use_container_width=True)



def plot_distribuzione_ordini(df_target):
    if df_target.empty:
        st.warning("Nessun dato disponibile.")
        return

    # 1. Pulizia rigorosa per Scala Log: SOLO valori strettamente positivi
    df_log = df_target[df_target['Totale'] > 0.1].copy()
    
    if df_log.empty:
        st.error("Dati non visualizzabili in scala logaritmica (tutti i valori sono <= 0.1).")
        return

    colori_personalizzati = {
        "Preventivo": "#A2D2FF", 
        "Ordine Aperto": "#B4E197", 
        "Ordine": "#4E944F"
    }

    # Creazione base
    fig = px.histogram(
        df_log, 
        x="Totale", 
        color="Tipo Doc.",
        marginal="box", 
        hover_data=['Oggetto', 'Data'],
        barmode='overlay', 
        color_discrete_map=colori_personalizzati,
        category_orders={"Tipo Doc.": ["Preventivo", "Ordine Aperto", "Ordine"]},
        log_x=True, # Attiviamo il log direttamente nel costruttore Express
        nbins=50
    )

    # 2. Configurazione selettiva delle tracce per evitare ValueError
    # Solo per i BOX
    fig.update_traces(
        selector=dict(type='box'),
        boxpoints='all', 
        jitter=0.5, 
        pointpos=0,
        marker=dict(size=4)
    )

    # Solo per l'ISTOGRAMMA
    fig.update_traces(
        selector=dict(type='histogram'),
        opacity=0.6
    )

    # 3. Layout Finale con correzione assi
    fig.update_layout(
        height=850,
        title="Distribuzione Valori (Scala Logaritmica)",
        title_x=0,
        # Definiamo i domini Y separatamente per dare spazio
        yaxis=dict(domain=[0, 0.45], title="Frequenza"), 
        yaxis2=dict(domain=[0.55, 1], title="Boxplot"),
        xaxis=dict(title="Importo Documento (€) - Log Scale"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(t=100, b=50, l=50, r=50),
        bargap=0.02
    )

    st.plotly_chart(fig, use_container_width=True)
    

def panoramica_articoli(df):
    """
    Grafico a torta Top 5 + Tabella completa con valori assoluti e percentuali.
    """

    if 'Oggetto' not in df.columns:
        st.error("Colonna 'Oggetto' non trovata.")
        return

    # 1. Preparazione Dati Completi (per la tabella)
    conteggio_totale = df['Oggetto'].value_counts().reset_index()
    conteggio_totale.columns = ['Oggetto', 'Assoluto']
    
    # Percentuali sul totale
    totale_pezzi = conteggio_totale['Assoluto'].sum()
    conteggio_totale['Percentuale'] = (conteggio_totale['Assoluto'] / totale_pezzi * 100).round(2)
    conteggio_totale['%'] = conteggio_totale['Percentuale'].astype(str) + '%'

    # 2. Grafico (Top 5 + Altro)
    if len(conteggio_totale) > 5:
        df_top = conteggio_totale.head(5).copy()
        somma_altri = conteggio_totale.iloc[5:]['Assoluto'].sum()
        riga_altro = pd.DataFrame({'Oggetto': ['RESTANTI'], 'Assoluto': [somma_altri]})
        df_plot = pd.concat([df_top, riga_altro], ignore_index=True)
    else:
        df_plot = conteggio_totale

    # 3. Output
    col1, col2 = st.columns([1.8, 1.2])

    with col1:
        fig_pie = px.pie(
            df_plot, 
            values='Assoluto', 
            names='Oggetto',
            title="Top 5 Oggetti e Incidenza",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        
        fig_pie.update_traces(textinfo='percent+label')
        
        # Legenda orizzontale in alto
        fig_pie.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            margin=dict(t=100, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.write("#### Analisi Dettagliata")
        # Mostriamo la tabella completa (voci univoche totali)
        # Selezioniamo solo le colonne che ci interessano per la tabella
        tabella_display = conteggio_totale[['Oggetto', 'Assoluto', '%']]
        
        st.dataframe(
            tabella_display, 
            hide_index=True, 
            use_container_width=True,
            height=400 # Altezza fissa con scrollbar se i dati sono molti
        )
        st.caption(f"Totale voci univoche rilevate: {len(conteggio_totale)}")






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
        df_orders = carica_dati_commerciali(uploaded_file_orders)
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
    
    # 1. Filtriamo il dataframe sui tre stadi: 
    # preventivo, ordine aperto e ordine chiuso
    stadi_target  = ["Preventivo", "Ordine Aperto", "Ordine"]
    df_target     = df_orders[df_orders['Tipo Doc.'].isin(stadi_target)]
    
    # 2. Aggregazione quantità e volumi
    conteggio_qty         = df_target['Tipo Doc.'].value_counts().reset_index()
    conteggio_qty.columns = ['Tipo Doc.', 'Conteggio'] 
    conteggio_vol         = df_target.groupby('Tipo Doc.')['Totale'].sum().reset_index()
    
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

        st.write("")
        st.write("")

        # 1. Mediana
        mediane = df_target.groupby('Tipo Doc.')['Totale'].median().reset_index()
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
        
        st.divider()
        st.write("#### Analisi Statistica della Distribuzione")
        plot_distribuzione_ordini(df_target)
        
        st.info("""
        **Come leggere questo grafico:**
        * **Istogramma (Sotto):** Indica dove si concentrano i tuoi volumi (es. molti ordini tra 500€ e 1000€).
        * **Box Plot (Sopra):** La linea centrale è la **Mediana**. I punti isolati sono gli **Outliers** (ordini eccezionalmente grandi).
        """)




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
