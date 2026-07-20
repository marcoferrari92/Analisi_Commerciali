import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import re
import json
import xarray
import numpy as np

st.set_page_config(layout="wide")

from eventi_panoramica import distribuzione_eventi
from eventi_performance_team import analisi_performance_utenti
from eventi_aziende import coinvolgimento_aziende
from eventi_loading import carica_eventi
from ordini_loading import carica_ordini
from ordini_pulizia_df import calcola_totale_riga
from ordini_panaromica import mostra_panoramica_ordini
from ordini_conversioni import analisi_conversione_preventivi
from ordini_riordino import elabora_gestionale
        




def DATA_range(df):
    
    date = df['DATA'].dropna()
    
    if not date.empty:
        d_min, d_max = date.min().date(), date.max().date()
        #st.info(f"📅 Dati disponibili: dal **{d_min.strftime('%d/%m/%Y')}** al **{d_max.strftime('%d/%m/%Y')}**")
        
        return d_min, d_max
        
    return None, None


def DATA_filtering(period, df):
    
    if isinstance(period, tuple) and len(period) == 2:
        #DATA_start, DATA_end = period
        df_filtrato = df[
                (df['DATA'].dt.date >= period[0]) & 
                (df['DATA'].dt.date <= period[1])
                ].copy()
        
    # Un piccolo avviso se manca una delle due date (inizio o fine)
    else:
        df_filtrato = df_events.copy()
        st.warning("Seleziona entrambe le date (inizio e fine) per filtrare.")

    return df_filtrato







# ***********************************************************************
#                                 MAIN APP
# ***********************************************************************


st.header("Analisi Commerciali")
st.divider()

# Inizializzazione
df_events = None
df_orders = None
# date calendario
date_min = None
date_max = None


# *****************
# CARICAMENTO FILE 
# *****************

# Inizializzazione variabili all'inizio dello script per evitare NameError
df_events = None
df_orders = None
date_min = None
date_max = None

st.subheader("Caricamento File")
col1, col2, col3 = st.columns(3)

with col1:
    st.write("#### Eventi")
    uploaded_file_events = st.file_uploader("Carica file eventi (formato CSV)", type="csv")
    if uploaded_file_events:
        df_events = carica_eventi(uploaded_file_events) 
        if df_events is not None:
            d_min_ev, d_max_ev = DATA_range(df_events)
            date_min, date_max = d_min_ev, d_max_ev

with col2:
    st.write("#### Ordini")
    uploaded_file_orders = st.file_uploader("Carica file ordini (formato JSON)", type="json")
    if uploaded_file_orders:
        df_orders = carica_ordini(uploaded_file_orders) 
        if df_orders is not None:
            d_min_or, d_max_or = DATA_range(df_orders)
            date_min, date_max = d_min_or, d_max_or


# --- SEZIONE FILTRO PERIODO ---
# Attiviamo i filtri solo se almeno uno dei due DF è stato creato
if date_min is not None and date_max is not None:
    with col3:
        st.write("#### Periodo Analisi")
        period = st.date_input(
            "Seleziona date:",
            value=(date_min, date_max),
            min_value=date_min,
            max_value=date_max
        )

    # Applichiamo il filtraggio solo se l'utente ha selezionato un range completo (inizio e fine)
    if isinstance(period, tuple) and len(period) == 2:
        if df_events is not None:
            df_events = DATA_filtering(period, df_events)
        
        #if df_orders is not None:
            #df_orders = DATA_filtering(period, df_orders)
    else:
        st.warning("Completa la selezione del periodo (Data inizio e Data fine).")
else:
    st.info("Carica almeno un file per attivare i filtri temporali.")



# ***********************************************************************
#                             ANALISI ORDINI 
# ***********************************************************************

st.divider()
st.subheader("Analisi Ordini e Preventivi")
st.write("")

if df_orders is not None: 
    
    # Toggle per l'IVA
    mostra_iva = st.toggle("Includi IVA nel totale", value=False)

    # Stampa tabella dentro un expander
    #with st.expander("Visualizza dati grezzi", expanded=False):
    #    st.dataframe(df_orders, use_container_width=True)
    
    # Calcolo importo totali documenti
    df_orders = calcola_totale_riga(df_orders, includi_iva=mostra_iva)
    
    #elabora_gestionale(df_orders)
    #df_ordini, df_aperti, df_pulito = elabora_gestionale(df_orders, period[0], period[1])
    df_pulito = elabora_gestionale(df_orders, period[0], period[1])
   
    
    if df_pulito is not None and not df_pulito.empty:
        
        # ********************************
        #  PANORAMICA ORDINI E PREVENTIVI
        # ********************************
        st.write("")
        #mostra_panoramica_ordini(df_ordini, df_aperti)
        mostra_panoramica_ordini(df_pulito, data_inizio=period[0], data_fine=period[1])
            
       
                        
    else:
        st.warning("⚠️ Nessun dato valido da analizzare dopo la pulizia del file JSON.")
        
    


# ***********************************************************************
#                             ANALISI EVENTI
# ***********************************************************************

if df_events is not None:
    

    st.divider()
    st.write("")
    st.subheader("Analisi Eventi")


    # FILTRO CAMPAGNE MARKETING

    # Controlliamo se la colonna CAMPAGNA esiste nel DataFrame
    if 'CAMPAGNA' in df_events.columns:
        # 1. Convertiamo in stringa e gestiamo i valori mancanti forzandoli a stringa vuota
        df_events['CAMPAGNA'] = df_events['CAMPAGNA'].fillna('').astype(str).str.strip().str.upper()
        
        # 2. Estraiamo i valori unici, escludendo quelli "vuoti" significativi
        campagne_uniche = df_events['CAMPAGNA'].unique()
        
        # 3. Pulizia usando una logica sicura
        # Escludiamo valori che dopo la pulizia risultano vuoti o equivalenti a NULL/NaN
        campagne_pulite = [
            c for c in campagne_uniche 
            if c and c not in ['NAN', 'NONE', 'NAT', 'NULL', '']
        ]
        
        # 4. Ordinamento sicuro
        campagne_pulite.sort()
        
        opzioni_campagna = ["TUTTE LE CAMPAGNE"] + campagne_pulite
        
        # Render del selettore
        st.write("")
        campagna_selezionata = st.selectbox(
            "🎯 **Filtra l'analisi per Campagna Marketing:**",
            options=opzioni_campagna,
            index=0  # Di default mostra "Tutte le campagne"
        )
        
        # Applichiamo il filtro al DataFrame solo se l'utente non ha scelto "Tutte le campagne"
        if campagna_selezionata != "TUTTE LE CAMPAGNE":
            df_events = df_events[df_events['CAMPAGNA'] == campagna_selezionata]
            
            # Controllo di sicurezza se il filtro svuota il dataframe
            if df_events.empty:
                st.warning("⚠️ Nessun dato disponibile per la campagna selezionata.")
                st.stop()
    else:
        st.info("ℹ️ Colonna 'CAMPAGNA' non trovata nel file. L'analisi mostrerà tutti i dati disponibili.")


    # PULIZIA STRINGHE
    df_events['TIPO EVENTO'] = df_events['TIPO EVENTO'].astype(str).str.strip()
    df_events['TIPO EVENTO'] = df_events['TIPO EVENTO'].str.replace('TELEFONATO -', 'TELEFONATO', regex=False)
    df_events = df_events[~df_events['TIPO EVENTO'].isin(['nan', 'None', '', 'NaN'])]

    # PANORAMICA EVENTI
    st.write("")
    st.write("")
    with st.expander("👁️ Panoramica Eventi"):
        distribuzione_eventi(df_events)


    # PERFORMANCE TEAM ---
    st.write("")
    st.write("")
    with st.expander("⚡️ Performance Team"):
        analisi_performance_utenti(df_events)

    
    # --- SEZIONE AZIENDE PIÙ COINVOLTE ---
    st.write("")
    st.write("")
    with st.expander("🏢 Analisi Coinvolgimento Aziende"):
        coinvolgimento_aziende(df_events)

    
        
