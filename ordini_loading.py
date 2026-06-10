import streamlit as st
import pandas as pd
import json

@st.cache_data
def carica_ordini(file):
    # 1. Caricamento JSON
    dati_json = json.load(file)
    righe_esplose = []

    # 2. Esplosione integrale
    for id_doc, doc in dati_json.items():
        # Info testata (escludiamo 'righe')
        info_doc = {k: v for k, v in doc.items() if k != 'righe'}
        
        # Righe
        righe = doc.get('righe', {})
        if isinstance(righe, dict) and righe:
            for id_riga, riga in righe.items():
                riga_flat = info_doc.copy()
                
                # Mappiamo le chiavi del JSON
                for k, v in riga.items():
                    # Se trovi 'quantita', chiamala 'QT'
                    if k == 'quantita':
                        riga_flat['QT'] = v
                    else:
                        riga_flat[k] = v
                        
                righe_esplose.append(riga_flat)
        else:
            righe_esplose.append(info_doc)

    # 3. Creazione DataFrame
    df = pd.DataFrame(righe_esplose)
    
    # 4. Forzatura MAIUSCOLE su tutte le colonne
    df.columns = [str(c).upper() for c in df.columns]
    
    # 5. Fix Data (obbligatorio per non crashare i filtri di app.py)
    if 'DATA' in df.columns:
        df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').fillna(pd.Timestamp('2026-01-01'))

    # 6. Stampa tabella
    with st.expander("Visualizza Tabella Dati", expanded=False):
        st.dataframe(df, use_container_width=True)

    return df