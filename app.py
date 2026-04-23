import streamlit as st
import pandas as pd

@st.cache_data
def carica_dati_commerciali(file):
    try:
        # Caricamento con separatore punto e virgola e encoding per file IT
        df = pd.read_csv(file, sep=';', encoding='latin1')
        if df.shape[1] <= 1:
            file.seek(0)
            df = pd.read_csv(file, sep=',', encoding='utf-8')
            
        # Pulizia nomi colonne
        df.columns = df.columns.str.strip()
        
        # TRASFORMAZIONE DATA: manteniamo solo la parte data (senza ore)
        if 'Data Evento' in df.columns:
            # Prima convertiamo in datetime
            df['Data Evento'] = pd.to_datetime(df['Data Evento'], dayfirst=True, errors='coerce')
            # Poi estraiamo solo la data per la visualizzazione
            df['Data Evento'] = df['Data Evento'].dt.date
            
        return df
    except Exception as e:
        st.error(f"Errore: {e}")
        return None

    # Pulizia nomi colonne
    df.columns = df.columns.str.strip()
    
    # Trasformazione data specifica per il tuo file
    if 'Data Evento' in df.columns:
        df['Data Evento'] = pd.to_datetime(df['Data Evento'], dayfirst=True, errors='coerce')
    
    return df




# Funzione per mostrare il periodo (come richiesto prima)
def mostra_periodo_analisi(df):
    if 'Data Evento' in df.columns:
        date_valide = df['Data Evento'].dropna()
        if not date_valide.empty:
            data_inizio = date_valide.min()
            data_fine = date_valide.max()
            inizio_str = data_inizio.strftime('%d/%m/%Y')
            fine_str = data_fine.strftime('%d/%m/%Y')
            st.info(f"📅 **Periodo Analizzato:** dal {inizio_str} al {fine_str}")
            return data_inizio, data_fine
    return None, None




# --- Esempio di utilizzo nella App ---
st.title("Analisi Attività Commerciali")

uploaded_file = st.file_uploader("Carica il file export_eventi", type="csv")

# --- Sezione Statistiche e Visualizzazione ---
if uploaded_file:
    df = carica_dati_commerciali(uploaded_file)
    
    if df is not None:
        mostra_periodo_analisi(df)

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
