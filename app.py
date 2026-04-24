import streamlit as st
import pandas as pd
import plotly.express as px
import re

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

        # PULIZIA TIPO EVENTO (Rimuove trattini, spazi e mette in Maiuscolo)
        if 'Tipo Evento' in df.columns:
            # Qui usiamo il modulo 're' importato sopra
            df['Tipo Evento'] = df['Tipo Evento'].apply(
                lambda x: re.sub(r'[^a-zA-Z\s]', '', str(x)).strip().upper()
            )
            
        return df
        
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return None
        
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


st.subheader("📆 Analisi Eventi")
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


        # --- SEZIONE 2: RESOCONTO ---
        st.divider()
        with st.expander("📊 Volume e Qualità delle Attività"):
        
            # --- PREPARAZIONE DATI ---
            # 1. Dati per Tipologia
            stats_tipo = df_filtrato['Tipo Evento'].value_counts().reset_index()
            stats_tipo.columns = ['Tipo Evento', 'Conteggio']
            
            # 2. Dati per Qualità Note
            df_qualita = df_filtrato.copy()
            df_qualita['Qualità'] = df_qualita['Note'].apply(
                lambda x: "UTILE (Con Note)" if pd.notnull(x) and str(x).strip() != "" else "INUTILE (Senza Note)"
            )
            stats_qualita = df_qualita['Qualità'].value_counts().reset_index()
            stats_qualita.columns = ['Stato Nota', 'Conteggio']
            
            # --- PRIMA RIGA: GRAFICO A TORTA TIPOLOGIE ---
            st.write("#### Tipologie Eventi")
            fig_pie_tipo = px.pie(
                stats_tipo, 
                values='Conteggio', 
                names='Tipo Evento', 
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie_tipo.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_pie_tipo, use_container_width=True)
            
            # --- SECONDA RIGA: TABELLA E TOTALE ---
            st.write("#### Riepilogo Volumi")
            col_tab, col_tot = st.columns([3, 1]) # Tabella più larga rispetto al numero totale
            
            with col_tab:
                st.dataframe(stats_tipo, hide_index=True, use_container_width=True)
            
            with col_tot:
                totale_attivita = len(df_filtrato)
                st.metric("Totale Attività", totale_attivita)
            
            # --- TERZA RIGA: QUALITÀ NOTE E PERCENTUALE ---
            st.divider()
            st.write("#### Analisi Qualità Note")
            with st.popover("💡 Analisi"):
                    st.info(""" 
                    Controlliamo la qualità degli eventi inseriti per il famoso teorema: 
                    *Garbage In, Garbage Out* (**GIGO**).
                    * ⚠️ **Issue 1:** Alcuni eventi sono privi di note e non apportano contenuto informativo (Eventi MUTI).
                        * 💡*Tip:* mettere un vincolo nel CRM per cui eventi senza note non possono essere caricati.
                    * ⚠️ **Issue 2:** molti eventi hanno note poco comprensibili.
                        * 💡*Tip:* strutturare il campo note con le classiche 5 W del giornalismo sarebbe utile.
                    """)

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
            st.plotly_chart(fig_pie_qual, use_container_width=True)


        # --- SEZIONE HEATMAP ORARIA ---
        with st.expander("📅 Heatmap Oraria"):        
            st.subheader("🕒 Distribuzione Oraria delle Attività")
               
            # 1. Estraiamo l'ora (come intero) e il nome del giorno
            df_heatmap = df_filtrato.copy()
            df_heatmap['Ora'] = pd.to_datetime(df_heatmap['Ora Evento'], format='%H:%M').dt.hour
            df_heatmap['Giorno_Num'] = pd.to_datetime(df_heatmap['Data Evento']).dt.dayofweek
            df_heatmap['Giorno'] = pd.to_datetime(df_heatmap['Data Evento']).dt.day_name()
            
            # Ordine dei giorni in italiano
            giorni_ordine = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            traduzione_giorni = {
                'Monday': 'Lunedì', 'Tuesday': 'Martedì', 'Wednesday': 'Mercoledì', 
                'Thursday': 'Giovedì', 'Friday': 'Venerdì', 'Saturday': 'Sabato', 'Sunday': 'Domenica'
            }
            
            # Raggruppiamo per Giorno e Ora
            heatmap_data = df_heatmap.groupby(['Giorno', 'Ora']).size().reset_index(name='Conteggio')
            
            # Creiamo una pivot per la heatmap
            pivot_heatmap = heatmap_data.pivot(index='Giorno', columns='Ora', values='Conteggio').fillna(0)
            
            # Ordiniamo i giorni correttamente (da Lunedì a Domenica)
            pivot_heatmap = pivot_heatmap.reindex([g for g in giorni_ordine if g in pivot_heatmap.index])
            # Rinominiamo i giorni in italiano per la visualizzazione
            pivot_heatmap.index = [traduzione_giorni[g] for g in pivot_heatmap.index]
            
            # Creazione del grafico con Plotly
            fig_heat = px.imshow(
                pivot_heatmap,
                labels=dict(x="Ora del Giorno", y="Giorno della Settimana", color="Numero Attività"),
                x=pivot_heatmap.columns,
                y=pivot_heatmap.index,
                color_continuous_scale='Viridis', # Scala cromatica leggibile
                text_auto=True, # Mostra i numeri dentro i quadratini
                aspect="auto"
            )
            
            fig_heat.update_layout(
                xaxis=dict(tickmode='linear'), # Mostra ogni singola ora sull'asse X
                height=450
            )
            
            st.plotly_chart(fig_heat, use_container_width=True)
            
            st.info("💡 **Consiglio:** Le zone più chiare indicano le fasce orarie con la massima densità di eventi. Utile per capire se il team concentra le chiamate al mattino o al pomeriggio.")
                    
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
