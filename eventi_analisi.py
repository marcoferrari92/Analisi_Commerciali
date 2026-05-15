import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def distribuzione_eventi(df_events):
    """
    Analisi della distribuzione eventi per tipo anagrafica.
    """
    
    # Verifichiamo che la colonna esista nel dataframe ricevuto
    if 'TIPO ANAGRAFICA' in df_events.columns:
        
        # Numeri eventi per Clienti, Prospect e Lead
        df_temp = df_events.copy()
        counts = df_temp['TIPO ANAGRAFICA'].value_counts()
        target_categories = ['CLIENTE', 'LEAD', 'PROSPECT']
        filtered_counts = counts.reindex(target_categories, fill_value=0)
        
        # Layout Streamlit: 2 colonne
        col0, col1, col2, col3, col4 = st.columns([0.5, 0.5, 0.5, 1, 0.5])
        
        with col1:
            st.dataframe(filtered_counts)
        
        with col3:
            
            # Creazione grafico con Matplotlib
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
            fig.patch.set_alpha(0) # Sfondo trasparente
            st.pyplot(fig)
    else:
        st.error(f"Colonna 'TIPO ANAGRAFICA' non trovata. Colonne presenti: {list(df_events.columns)}")
