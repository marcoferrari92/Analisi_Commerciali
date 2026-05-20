import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def distribuzione_eventi(df_events):
    """
    Analisi della distribuzione eventi per tipo anagrafica e dettaglio tipo evento.
    Con opzione di visualizzazione in valori assoluti o percentuali.
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
            df_temp['TIPO EVENTO'] = df_temp['TIPO EVENTO'].str.strip() 
            
            # Filtriamo il dataframe solo per le 3 categorie target per pulizia
            df_filtered_types = df_temp[df_temp['TIPO ANAGRAFICA'].isin(target_categories)]
            
            # Creiamo la tabella pivot (Crosstab)
            pivot_df = pd.crosstab(df_filtered_types['TIPO ANAGRAFICA'], df_filtered_types['TIPO EVENTO'])
            
            # Reindicizziamo le righe
            pivot_df = pivot_df.reindex(target_categories, fill_value=0)
            pivot_df.index = [idx.capitalize() for idx in pivot_df.index]
            
            # ---------------------------------------------------------
            # AGGIUNTA: Selezione Tipo di Visualizzazione
            # ---------------------------------------------------------
            tipo_visualizzazione = st.radio(
                "Seleziona la modalità di visualizzazione del grafico:",
                ["Valori Assoluti", "Percentuale (Comportamento Commerciale)"],
                horizontal=True
            )
            
            # Prepariamo i dati in base alla scelta dell'utente
            if tipo_visualizzazione == "Percentuale (Comportamento Commerciale)":
                # Dividiamo ogni riga per la sua somma e moltiplichiamo per 100
                plot_data = pivot_df.div(pivot_df.sum(axis=1), axis=0) * 100
                xlabel_text = "Percentuale sul Totale Attività (%)"
            else:
                plot_data = pivot_df
                xlabel_text = "Numero di Eventi"
            # ---------------------------------------------------------
            
            # DEFINIZIONE COLORI ACCOPPIATI (Mantenuta la tua palette)
            color_mapping = {
                # Coppia Visite (Giallo)
                'VISITARE': '#ffff00',       
                'VISITATO': '#ffcc00',       
                
                # Coppia Telefonate (Rosa / Viola)
                'TELEFONARE': '#ff66ff',     
                'TELEFONATO': '#af7ac5',     
                
                # Coppia Email (Verde nel tuo snippet attuale)
                'INVIARE EMAIL': '#66ff66',   
                'INVIATA MAIL': '#009900',    
                'INVIO E-MAIL SFC': '#009900', 
                
                # Altri eventi singoli
                'PARTECIPAZIONE WEBINAR': '#3498db', 
                'SOLLECITARE OFFERTA COMMERCIALE': '#000000' 
            }
            
            # Creiamo la lista dei colori nell'ordine ESATTO delle colonne della pivot
            colors_list = [color_mapping.get(col, '#bdc3c7') for col in plot_data.columns]
            
            # Disegniamo il grafico
            fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
            
            # Usiamo plot_data che contiene o i valori assoluti o le percentuali
            plot_data.plot(kind='barh', stacked=True, ax=ax_bar, color=colors_list)
            
            # Estetica del grafico
            ax_bar.set_title("Distribuzione delle attività", fontsize=14, pad=15)
            ax_bar.set_xlabel(xlabel_text, fontsize=12)
            ax_bar.set_ylabel("Tipo Anagrafica", fontsize=12)
            ax_bar.legend(title="Tipo Evento", bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # Se la visualizzazione è in percentuale, impostiamo il limite dell'asse X a 100
            if tipo_visualizzazione == "Percentuale (Comportamento Commerciale)":
                ax_bar.set_xlim(0, 100)
                # Aggiunge il simbolo % ai numeri dell'asse X
                ax_bar.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}%'))
            
            # Pulizia bordi del grafico
            ax_bar.spines['top'].set_visible(False)
            ax_bar.spines['right'].set_visible(False)
            
            fig_bar.patch.set_alpha(0) # Sfondo trasparente per Streamlit
            
            # Mostriamo il grafico a tutta larghezza
            st.pyplot(fig_bar)
            
        else:
            st.warning("Colonna 'TIPO EVENTO' non trovata. Impossibile mostrare il dettaglio delle attività.")
            
    else:
        st.error(f"Colonna 'TIPO ANAGRAFICA' non trovata. Colonne presenti: {list(df_events.columns)}")
