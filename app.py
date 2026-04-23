import streamlit as st
import pandas as pd

@st.cache_data
def carica_dati_commerciali(file):
    # Carichiamo il file con i nomi corretti delle colonne
    df = pd.read_csv(file)
    
    # Pulizia nomi colonne per sicurezza
    df.columns = df.columns.str.strip()
    
    # Conversione della colonna 'Data Evento' in formato data
    # Il formato sembra essere GG/MM/AAAA
    df['Data Evento'] = pd.to_datetime(df['Data Evento'], dayfirst=True, errors='coerce')
    
    # Pulizia della colonna Utente (i tuoi commerciali)
    df['Utente'] = df['Utente'].astype(str).str.strip()
    
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
    
    st.bar_chart(data=stats, x='Commerciale', y='Numero Attività')
    
    # Tabella dettagliata
    st.write("Dettaglio eventi caricati:")
    st.dataframe(df[['Utente', 'Data Evento', 'Tipo Evento', 'Ragione Sociale']])
