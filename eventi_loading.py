

@st.cache_data
def carica_dati_eventi(file):
    try:
        # 1. Lettura file con gestione separatore
        df = pd.read_csv(file, sep=';', encoding='utf-8-sig')
        if df.shape[1] <= 1:
            file.seek(0)
            df = pd.read_csv(file, sep=',', encoding='utf-8-sig')

        # 2. Pulizia preliminare spazi e caratteri invisibili (BOM)
        df.columns = df.columns.str.strip().str.replace('ï»¿', '', regex=False)
        
        # Rinominiamo 'Data Evento' in 'DATA' per le tue funzioni di filtraggio
        if 'Data Evento' in df.columns:
            df = df.rename(columns={'Data Evento': 'DATA'})
        
        # Trasformiamo TUTTI i nomi delle colonne in maiuscolo
        df.columns = [c.upper() for c in df.columns]

        # 4. Controllo colonne obbligatorie (Tutte tranne CAMPAGNA)
        # Queste sono le colonne del tuo file eventi.csv dopo la trasformazione in maiuscolo
        colonne_necessarie = [
            'TIPO ANAGRAFICA', 'ID CLIENTI', 'RAGIONE SOCIALE', 
            'DATA', 'ORA EVENTO', 'TIPO EVENTO', 'UTENTE', 'NOTE'
        ]
        
        mancanti = [c for c in colonne_necessarie if c not in df.columns]
        
        if mancanti:
            st.error(f"⚠️ Errore: Il file non contiene tutte le colonne necessarie.")
            st.info(f"Colonne mancanti: {mancanti}")
            return None

        # 5. Gestione specifica della DATA
        df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce')
        righe_nulle = df['DATA'].isna().sum()
        df = df.dropna(subset=['DATA'])
        
        if righe_nulle > 0:
            st.warning(f"⚠️ Rimosse {righe_nulle} righe con DATA non valida o vuota.")

        # 6. Pulizia testi (Maiuscolo e rimozione spazi)
        # Rendiamo tutto maiuscolo per evitare discrepanze nei filtri (es. 'telefonata' vs 'TELEFONATA')
        colonne_testo = ['UTENTE', 'TIPO EVENTO', 'TIPO ANAGRAFICA', 'RAGIONE SOCIALE']
        for col in colonne_testo:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()

        return df

    except Exception as e:
        st.error(f"❌ Errore critico nel caricamento: {e}")
        return None
