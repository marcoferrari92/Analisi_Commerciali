import streamlit as st
import pandas as pd

@st.cache_data
def carica_ordini(file):
    
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

        # 4. Gestione specifica della DATA
        df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce')
        righe_nulle = df['DATA'].isna().sum()
        df = df.dropna(subset=['DATA'])
        
        if righe_nulle > 0:
            st.warning(f"⚠️ Rimosse {righe_nulle} righe con DATA non valida.")

        return df

    except Exception as e:
        st.error(f"Errore critico caricamento: {e}")
        return None
