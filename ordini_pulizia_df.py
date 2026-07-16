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
    df = df.copy()
    
    # 1. Pulizia standard
    colonne_numeriche = ['QT', 'PREZZO', 'SCONTO_IMPORTO']
    for col in colonne_numeriche:
        df[col] = df[col].apply(converti_valore) if col in df.columns else 0.0
    
    # 2. Calcoliamo il valore netto della riga (senza sommare nulla)
    # Se è una riga normale: (QT * PREZZO) - SCONTO_IMPORTO
    # Se è una riga di sconto (RIGA_SCONTO_TOTALE == 'SI'):
    # allora il valore della riga DEVE essere il PREZZO negativo.
    
    df['TOTALE_RIGA'] = (df['QT'] * df['PREZZO']) -(df['QT'] * df['SCONTO_IMPORTO'])
    #df['TOTALE_RIGA'] = (df['QT'] * df['PREZZO'])
    
    mask_sconto = df['RIGA_SCONTO_TOTALE'].astype(str).str.upper() == 'SI'
    
    # Sovrascriviamo il valore delle righe di sconto
    # Qui forziamo il valore a essere il negativo del prezzo indicato nella riga di sconto
    df.loc[mask_sconto, 'TOTALE_RIGA'] = -1 * df.loc[mask_sconto, 'PREZZO'].abs()
    
    # 3. Gestione IVA
    if includi_iva and 'CODICE_IVA' in df.columns:
        iva_perc = df['CODICE_IVA'].apply(converti_valore) / 100
        df['TOTALE_RIGA'] = df['TOTALE_RIGA'] * (1 + iva_perc)
            
    return df