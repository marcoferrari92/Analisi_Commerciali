import streamlit as st
import pandas as pd

@st.cache_data
def carica_dati_commerciali(file):
    try:
        # Proviamo a leggere con il punto e virgola (standard Excel IT)
        # Usiamo 'latin1' o 'utf-8-sig' per evitare errori sui caratteri accentati
        df = pd.read_csv(file, sep=';', encoding='latin1')
        
        # Se pandas legge una sola colonna, significa che il separatore era sbagliato
        if df.shape[1] <= 1:
            file.seek(0) # Reset del puntatore del file
            df = pd.read_csv(file, sep=',', encoding='utf-8')
            
    except Exception as e:
        st.error(f"Errore tecnico nel parsing: {e}")
        return None

    # Pulizia nomi colonne
    df.columns = df.columns.str.strip()
    
    # Trasformazione data specifica per il tuo file
    if 'Data Evento' in df.columns:
        df['Data Evento'] = pd.to_datetime(df['Data Evento'], dayfirst=True, errors='coerce')
    
    return df




def mostra_periodo_analisi(df):
    """Calcola e visualizza l'intervallo temporale dei dati."""
    if 'Data Evento' in df.columns:
        # Rimuoviamo eventuali valori nulli per il calcolo del periodo
        date_valide = df['Data Evento'].dropna()
        
        if not date_valide.empty:
            data_inizio = date_valide.min()
            data_fine = date_valide.max()
            
            # Formattiamo le date per la visualizzazione (GG/MM/AAAA)
            inizio_str = data_inizio.strftime('%d/%m/%Y')
            fine_str = data_fine.strftime('%d/%m/%Y')
            
            # Calcolo dei giorni totali
            giorni = (data_fine - data_inizio).days + 1
            
            # Visualizzazione in Streamlit
            st.info(f"📅 **Periodo Analizzato:** dal {inizio_str} al {fine_str} ({giorni} giorni)")
            
            return data_inizio, data_fine
    return None, None




# --- Esempio di utilizzo nella App ---
st.title("Analisi Attività Commerciali")

uploaded_file = st.file_uploader("Carica il file export_eventi", type="csv")

if uploaded_file:
    df = carica_dati_commerciali(uploaded_file)
    
    if df is not None:

        # PERIODO 
        data_min, data_max = mostra_periodo_analisi(df)
        
        st.sidebar.header("Filtro Temporale")
        periodo_selezionato = st.sidebar.date_input(
            "Seleziona intervallo",
            value=(data_min, data_max),
            min_value=data_min,
            max_value=data_max
        )

    
    st.subheader("Conteggio attività per Commerciale")
        
        # Prepariamo i dati per il grafico
        stats = df['Utente'].value_counts().reset_index()
        stats.columns = ['Commerciale', 'Numero Attività']
        
        # Grafico ORIZZONTALE: 
        # In Streamlit bar_chart, se mettiamo 'Commerciale' su y e 'Numero Attività' su x,
        # otteniamo barre che partono da sinistra verso destra.
        st.bar_chart(data=stats, x='Numero Attività', y='Commerciale')
        
        # Tabella dettagliata con l'orario
        st.write("Dettaglio eventi caricati:")
        
        # Verifichiamo che le colonne esistano prima di mostrarle per evitare errori
        colonne_da_mostrare = ['Utente', 'Data Evento', 'Ora Evento', 'Tipo Evento', 'Ragione Sociale']
        colonne_presenti = [col for col in colonne_da_mostrare if col in df.columns]
        
        st.dataframe(df[colonne_presenti])
