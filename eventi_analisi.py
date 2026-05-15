import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

"""
Riceve il dataframe degli eventi e visualizza metriche e grafico a torta
per le categorie CLIENTE, LEAD e PROSPECT.
"""

def distribuzione_eventi(df_events):

    import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def distribuzione_eventi(df_events):
    
    # 1. Controllo corretto: verifichiamo le colonne nel dataframe ricevuto in input
    if 'TIPO ANAGRAFICA' in df_events.columns      
        
        # Conteggio eventi nelle tre categorie
        df_temp = df_events.copy()
        counts = df_temp['TIPO ANAGRAFICA'].value_counts()
        target_categories = ['CLIENTE', 'LEAD', 'PROSPECT']
        filtered_counts = counts.reindex(target_categories, fill_value=0)
        
        # 3. Interfaccia Streamlit
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Dati Numerici")
            # Nota: filtered_counts è una Serie, Streamlit la visualizza bene
            st.dataframe(filtered_counts, column_config={"value": "Totale Eventi"})
            
            # Metriche dashboard
            for cat in target_categories:
                st.metric(label=cat.capitalize(), value=int(filtered_counts[cat]))
        
        with col2:
            st.subheader("Distribuzione Percentuale")
            
            fig, ax = plt.subplots(figsize=(8, 8))
            colors = ['#5dade2', '#58d68d', '#ec7063'] 
            
            ax.pie(
                filtered_counts, 
                labels=[c.capitalize() for c in filtered_counts.index], 
                autopct='%1.1f%%', 
                startangle=140, 
                colors=colors,
                textprops={'fontsize': 14}
            )
            ax.axis('equal') 
            fig.patch.set_alpha(0) # Rende lo sfondo del grafico trasparente
            st.pyplot(fig)
            
    else:
        st.error("⚠️ La colonna 'TIPO ANAGRAFICA' non è stata trovata nel file.")
