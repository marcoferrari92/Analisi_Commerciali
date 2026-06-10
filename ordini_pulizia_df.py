import pandas as pd
import re

def converti_valore(val):
    try:
        if pd.isna(val): return 0.0
        val_str = str(val).strip().replace(' ', '')
        if '.' in val_str and ',' in val_str:
            val_str = val_str.replace('.', '').replace(',', '.')
        elif ',' in val_str:
            val_str = val_str.replace(',', '.')
        pulito = re.sub(r'[^0-9.-]', '', val_str)
        return float(pulito) if pulito else 0.0
    except:
        return 0.0

def calcola_totale_riga(df, includi_iva=False):
    """
    Usa converti_valore per pulire i dati, calcola TOTALE_RIGA 
    e gestisce l'IVA.
    """
    df = df.copy()
    
    # 1. Pulizia usando la tua funzione converti_valore
    for col in ['QT', 'PREZZO']:
        if col in df.columns:
            df[col] = df[col].apply(converti_valore)
    
    # 2. Calcolo totale base
    df['TOTALE_RIGA'] = df['QT'] * df['PREZZO']
    
    # 3. Switch IVA
    if includi_iva and 'CODICE_IVA' in df.columns:
        # Pulisce anche l'IVA nel caso non sia un numero pulito
        iva_perc = df['CODICE_IVA'].apply(converti_valore) / 100
        df['TOTALE_RIGA'] = df['TOTALE_RIGA'] * (1 + iva_perc)
            
    return df