import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(layout="wide")

@st.cache_data
def carica_dati_commerciali(file):
    try:
        # Caricamento con gestione encoding e delimitatori
        df = pd.read_csv(file, sep=';', encoding='latin1')
        if df.shape[1] <= 1:
            file.seek(0)
            df = pd.read_csv(file, sep=',', encoding='utf-8')
        
        df.columns = df.columns.str.strip()
        
        # Conversione Date robusta
        if 'Data Evento' in df.columns:
            df['Data Evento'] = pd.to_datetime(df['Data Evento'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Data Evento'])

        # Pulizia Tipo Evento
        if 'Tipo Evento' in df.columns:
            df['Tipo Evento'] = df['Tipo Evento'].apply(
                lambda x: re.sub(r'[^a-zA-Z\s]', '', str(x)).strip().upper()
            )
            
        return df
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return None




def mostra_periodo_analisi(df):
    date_valide = df['Data Evento'].dropna()
    if not date_valide.empty:
        d_min, d_max = date_valide.min().date(), date_valide.max().date()
        st.info(f"📅 **Dati disponibili nel file:** dal {d_min.strftime('%d/%m/%Y')} al {d_max.strftime('%d/%m/%Y')}")
        return d_min, d_max
    return None, None

# --- MAIN APP ---


st.subheader("Analisi Eventi")
uploaded_file = st.file_uploader("Carica CSV", type="csv")

if uploaded_file:
    df = carica_dati_commerciali(uploaded_file)
    
    if df is not None:
        
        # --- FILTRO TEMPORALE IN AREA PRINCIPALE (LAYOUT OTTIMIZZATO) ---
        
        # 1. Recuperiamo i limiti temporali dal file
        date_valide = df['Data Evento'].dropna()
        if not date_valide.empty:
            data_min_file, data_max_file = date_valide.min().date(), date_valide.max().date()
            
            st.markdown("#### 📅 Selezione Periodo di Analisi")
            
            # Creiamo due colonne: una per l'info e una per il filtro
            col_info_date, col_input_date = st.columns(2)
            
            with col_info_date:
                # Mostriamo il range disponibile nel file
                st.info(f"**Dati disponibili:** dal {data_min_file.strftime('%d/%m/%Y')} al {data_max_file.strftime('%d/%m/%Y')}")
                # Filtro interattivo sulla stessa riga
                periodo_selezionato = st.date_input(
                    "Filtra per intervallo:",
                    value=(data_min_file, data_max_file),
                    min_value=data_min_file,
                    max_value=data_max_file,
                    label_visibility="collapsed" # Nasconde l'etichetta per pulizia, l'utente capisce dal contesto
                )
            
            with col_input_date:
                st.write("")
            
            # Logica di filtraggio
            if isinstance(periodo_selezionato, tuple) and len(periodo_selezionato) == 2:
                data_inizio, data_fine = periodo_selezionato
                df_filtrato = df[(df['Data Evento'].dt.date >= data_inizio) & 
                                 (df['Data Evento'].dt.date <= data_fine)].copy()
            else:
                df_filtrato = df.copy()
                # Un piccolo avviso se manca una delle due date (inizio o fine)
                st.warning("Seleziona entrambe le date (inizio e fine) per filtrare.")
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
                lambda x: "UTILE (Con Note)" if pd.notnull(x) and str(x).strip() != "" else "MUTO (Senza Note)"
            )
            stats_qualita = df_qualita['Qualità'].value_counts().reset_index()
            stats_qualita.columns = ['Stato Nota', 'Conteggio']
            
            # --- PRIMA RIGA: GRAFICO A TORTA TIPOLOGIE ---
            col1, col2 = st.columns([3, 1]) 
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
                    # Riduciamo il margine superiore da 80 a 40 o 50
                    margin=dict(t=50, l=10, r=10, b=10), 
                    coloraxis_colorbar=dict(
                        title="Intensità Attività",
                        thicknessmode="pixels", thickness=12, # Barra un po' più sottile
                        lenmode="fraction", len=0.4,           # Barra un po' più corta per eleganza
                        yanchor="bottom",                     # Ancoraggio al fondo della barra
                        y=1.02,                               # Posizionata appena sopra il grafico (1.0 è il bordo)
                        xanchor="center", x=0.5,
                        orientation="h"
                    )
                )
                st.plotly_chart(fig_pie_tipo, use_container_width=True)

            with col2: 
                totale_attivita = len(df_filtrato)
                st.write("")
                st.write("")
                st.metric("Totale Attività", totale_attivita)
                st.dataframe(stats_tipo, hide_index=True, use_container_width=True)
                
            
            # --- SECONDA RIGA: TABELLA E TOTALE ---
            st.write("#### Riepilogo Volumi")
            col_tab, col_tot = st.columns([3, 1]) 
            
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

            
    # --- SEZIONE AZIENDE PIÙ COINVOLTE ---
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
