import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def visualizza_distribuzione_eventi(df_events):
    """
    Riceve il dataframe degli eventi e visualizza metriche e grafico a torta
    per le categorie CLIENTE, LEAD e PROSPECT.
    """
    # 1. Pulizia e normalizzazione (opzionale ma consigliata)
    # Assicuriamoci che i valori siano confrontabili convertendoli in maiuscolo
    df_temp = df_events.copy()
    df_temp['TIPO ANAGRAFICA'] = df_temp['TIPO ANAGRAFICA'].astype(str).str.upper()

    # 2. Conteggio eventi
    counts = df_temp['TIPO ANAGRAFICA'].value_counts()
    
    # 3. Filtriamo le tre categorie richieste
    target_categories = ['CLIENTE', 'LEAD', 'PROSPECT']
    filtered_counts = counts.reindex(target_categories, fill_value=0)

    # 4. Creazione Interfaccia Streamlit
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Dati Numerici")
        # Visualizzazione tabella pulita
        st.dataframe(filtered_counts, column_config={"value": "Totale Eventi"})
        
        # Opzionale: Aggiunta di metriche rapide per un look più "dashboard"
        for cat in target_categories:
            st.metric(label=cat.capitalize(), value=int(filtered_counts[cat]))

    with col2:
        st.subheader("Distribuzione Percentuale")
        
        # Creazione del grafico con Matplotlib
        fig, ax = plt.subplots(figsize=(8, 8))
        colors = ['#5dade2', '#58d68d', '#ec7063'] # Azzurro, Verde, Rosso soft
        
        ax.pie(
            filtered_counts, 
            labels=[c.capitalize() for c in filtered_counts.index], 
            autopct='%1.1f%%', 
            startangle=140, 
            colors=colors,
            textprops={'fontsize': 14}
        )
        ax.axis('equal')  # Cerchio perfetto
        
        # Rimozione dello sfondo bianco della figura per integrarsi meglio in Streamlit
        fig.patch.set_alpha(0)
        
        st.pyplot(fig)

# Esempio di utilizzo all'interno della tua app:
# if df_events is not None:
#     visualizza_distribuzione_eventi(df_events)
