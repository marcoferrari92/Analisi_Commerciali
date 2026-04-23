import streamlit as st
import pandas as pd
import plotly.express as px

@st.cache_data
def carica_dati_commerciali(file):
    try:
        # Caricamento standard per export IT
        df = pd.read_csv(file, sep=';', encoding='latin1')
        if df.shape[1] <= 1:
            file.seek(0)
            df = pd.read_csv(file, sep=',', encoding='utf-8')
        
        df.columns = df.columns.str.strip()
        
        if 'Data Evento' in df.columns:
            # Convertiamo in datetime e poi estraiamo solo .date()
            df['Data Evento'] = pd.to_datetime(df['Data Evento'], dayfirst=True, errors='coerce').dt.date
            
        return df
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return None

def mostra_periodo_analisi(df):
    date_valide = df['Data Evento'].dropna()
    if not date_valide.empty:
        d_min, d_max = min(date_valide), max(date_valide)
        st.info(f"📅 **Dati disponibili:** dal {d_min.strftime('%d/%m/%Y')} al {d_max.strftime('%d/%m/%Y')}")
        return d_min, d_max
    return None, None

# --- MAIN APP ---
uploaded_file = st.file_uploader("Carica CSV", type="csv")

if uploaded_file:
    df = carica_dati_commerciali(uploaded_file)
    
    if df is not None:

        # PERIODO ****************
        
        # 1. Recuperiamo i limiti temporali del file
        data_min_file, data_max_file = mostra_periodo_analisi(df)

        # 2. Sidebar con lo slider (FILTRO ATTIVO)
        st.sidebar.header("Filtro Temporale")
        periodo_selezionato = st.sidebar.date_input(
            "Visualizza attività nel periodo:",
            value=(data_min_file, data_max_file),
            min_value=data_min_file,
            max_value=data_max_file
        )

        # 3. APPLICAZIONE DEL FILTRO
        if isinstance(periodo_selezionato, tuple) and len(periodo_selezionato) == 2:
            start_date, end_date = periodo_selezionato
            df_filtrato = df[(df['Data Evento'] >= start_date) & (df['Data Evento'] <= end_date)]
        else:
            df_filtrato = df 

        #*************************


        # --- SEZIONE 2: RESOCONTO (GRAFICO A TORTA) ---
        st.divider()
        st.subheader("Resoconto Tipologia Attività")
        

         # Preparazione dati per la torta
        stats_tipo = df_filtrato['Tipo Evento'].value_counts().reset_index()
        stats_tipo.columns = ['Tipo Evento', 'Conteggio']
            
        fig_pie = px.pie(
                stats_tipo, 
                values='Conteggio', 
                names='Tipo Evento', 
                hole=0.4, # Trasforma in grafico a ciambella, più leggibile
                color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
            

        st.write("#### Volumi Totali")
        totale_attivita = len(df_filtrato)
        st.metric("Totale Eventi", totale_attivita)
            
        # Mostriamo la lista pesata delle attività
        st.dataframe(stats_tipo, hide_index=True, use_container_width=True)

        
        
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
        col_view = ['Utente', 'Data Evento', 'Ora Evento', 'Tipo Evento', 'Ragione Sociale']
        col_presenti = [c for c in col_view if c in df_filtrato.columns]
        
        st.dataframe(
            df_filtrato[col_presenti].sort_values(by=['Data Evento', 'Ora Evento'], ascending=False),
            use_container_width=True
        )
