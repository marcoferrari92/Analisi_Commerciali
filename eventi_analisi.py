import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def distribuzione_eventi(df_events):
    """
    Analisi della distribuzione eventi per tipo anagrafica e dettaglio tipo evento.
    """
    
    # Verifichiamo che la colonna principale esista
    if 'TIPO ANAGRAFICA' in df_events.columns:
        
        # Numeri eventi per Clienti, Prospect e Lead
        df_temp = df_events.copy()
        counts = df_temp['TIPO ANAGRAFICA'].value_counts()
        target_categories = ['CLIENTE', 'LEAD', 'PROSPECT']
        filtered_counts = counts.reindex(target_categories, fill_value=0)
        
        # Layout Streamlit: Colonne per la prima riga (Tabella + Torta)
        col0, col1, col2, col3, col4 = st.columns([0.5, 0.5, 0.5, 1, 0.5])
        
        with col1:
            st.write("**Totale per Categoria:**")
            st.dataframe(filtered_counts)
        
        with col3:
            # Creazione grafico a torta con Matplotlib
            fig, ax = plt.subplots(figsize=(6, 6))
            colors = ['#5dade2', '#58d68d', '#ec7063'] 
            
            ax.pie(
                filtered_counts, 
                labels=[c.capitalize() for c in filtered_counts.index], 
                autopct='%1.1f%%', 
                startangle=140, 
                colors=colors,
                textprops={'fontsize': 12}
            )
            ax.axis('equal') 
            fig.patch.set_alpha(0) # Sfondo trasparente
            st.pyplot(fig)
            
        # --- NUOVA SEZIONE: Dettaglio TIPO EVENTO ---
        if 'TIPO EVENTO' in df_events.columns:
            st.markdown("---")
            st.subheader("Dettaglio Tipologia di Evento per Anagrafica")
            
            # 1. PULIZIA DATI: Rimuoviamo il trattino da 'TELEFONATO -' e normalizziamo gli spazi
            df_temp['TIPO EVENTO'] = df_temp['TIPO EVENTO'].astype(str).str.replace('TELEFONATO -', 'TELEFONATO', regex=False)
            df_temp['TIPO EVENTO'] = df_temp['TIPO EVENTO'].str.strip() # Rimuove eventuali spazi bianchi finali residui
            
            # Filtriamo il dataframe solo per le 3 categorie target per pulizia
            df_filtered_types = df_temp[df_temp['TIPO ANAGRAFICA'].isin(target_categories)]
            
            # Creiamo una tabella pivot (Crosstab) - Ora 'TELEFONATO' sarà un'unica colonna pulita
            pivot_df = pd.crosstab(df_filtered_types['TIPO ANAGRAFICA'], df_filtered_types['TIPO EVENTO'])
            
            # Reindicizziamo le righe
            pivot_df = pivot_df.reindex(target_categories, fill_value=0)
            pivot_df.index = [idx.capitalize() for idx in pivot_df.index]
            
            # ---------------------------------------------------------
            # DEFINIZIONE COLORI ACCOPPIATI (Chiaro per l'azione, Scuro per il completato)
            # ---------------------------------------------------------
            color_mapping = {
                # Coppia Visite (Giallo)
                'VISITARE': '#ffff00',       # Giallo molto chiaro
                'VISITATO': '#ffcc00',       # Giallo scuro / dorato
                
                # Coppia Telefonate (Rosa / Viola)
                'TELEFONARE': '#ff66ff',     # Rosa chiaro
                'TELEFONATO': '#af7ac5',     # Viola / Rosa scuro (Trattino rimosso definitivamente)
                
                # Coppia Email (Azzurro / Blu)
                'INVIARE EMAIL': '#66ff66',   # Acqua/Azzurro chiaro
                'INVIATA MAIL': '#009900',    # Acqua medio
                'INVIO E-MAIL SFC': '#003300', # Verde acqua / Blu più intenso
                
                # Altri eventi singoli
                'PARTECIPAZIONE WEBINAR': '#3498db', # Blu
                'SOLLECITARE OFFERTA COMMERCIALE': '#000000' # Verde
            }
            
            # Creiamo la lista dei colori nell'ordine ESATTO delle colonne della pivot
            colors_list = [color_mapping.get(col, '#bdc3c7') for col in pivot_df.columns]
            # ---------------------------------------------------------
            
            # Disegniamo il grafico passando la lista di colori personalizzata
            fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
            
            pivot_df.plot(kind='barh', stacked=True, ax=ax_bar, color=colors_list)
            
            # Estetica del grafico
            ax_bar.set_title("Distribuzione delle attività", fontsize=14, pad=15)
            ax_bar.set_xlabel("Numero di Eventi", fontsize=12)
            ax_bar.set_ylabel("Tipo Anagrafica", fontsize=12)
            ax_bar.legend(title="Tipo Evento", bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # Pulizia bordi del grafico
            ax_bar.spines['top'].set_visible(False)
            ax_bar.spines['right'].set_visible(False)
            
            fig_bar.patch.set_alpha(0) # Sfondo trasparente per Streamlit
            
            # Mostriamo il grafico a tutta larghezza
            st.pyplot(fig_bar)
            
    else:
        st.error(f"Colonna 'TIPO ANAGRAFICA' non trovata. Colonne presenti: {list(df_events.columns)}")
