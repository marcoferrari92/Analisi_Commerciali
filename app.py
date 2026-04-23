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

# --- Esempio di utilizzo nella App ---
st.title("Analisi Attività Commerciali")

uploaded_file = st.file_uploader("Carica il file export_eventi", type="csv")

if uploaded_file:
    df = carica_dati_commerciali(uploaded_file)
    
    # Mostriamo le statistiche base per "Utente"
    st.subheader("Conteggio attività per Commerciale")
    stats = df['Utente'].value_counts().reset_index()
    stats.columns = ['Commerciale', 'Numero Attività']
    
    st.bar_chart(data=stats, x='Numero Attività', y='Commerciale')
    
    # Tabella dettagliata
    st.write("Dettaglio eventi caricati:")
    st.dataframe(df[['Utente', 'Data Evento', 'Tipo Evento', 'Ragione Sociale']])
