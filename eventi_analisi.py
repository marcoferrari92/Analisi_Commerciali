import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def distribuzione_eventi(df_events):
    """
    Analisi della distribuzione eventi per tipo anagrafica e dettaglio tipo evento.
    In modalità percentuale mostra la quota di ogni attività (colonna) distribuita sui target.
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
            
            # Creiamo una tabella pivot (Crosstab)
            pivot_df = pd.crosstab(df_filtered_types['TIPO ANAGRAFICA'], df_filtered_types['TIPO EVENTO'])
            
            # Reindicizziamo le righe
            pivot_df = pivot_df.reindex(target_categories, fill_value=0)
            pivot_df.index = [idx.capitalize() for idx in pivot_df.index]
            
            # DEFINIZIONE COLORI ACCOPPIATI (Tua mappa per valori assoluti)
            color_mapping_eventi = {
                'VISITARE': '#ffff00',       
                'VISITATO': '#ffcc00',       
                'TELEFONARE': '#ff66ff',     
                'TELEFONATO': '#af7ac5',     
                'INVIARE EMAIL': '#66ff66',   
                'INVIATA MAIL': '#009900',    
                'INVIO E-MAIL SFC': '#009900', 
                'PARTECIPAZIONE WEBINAR': '#3498db', 
                'SOLLECITARE OFFERTA COMMERCIALE': '#000000' 
            }
            
            # ---------------------------------------------------------
            # SELEZIONE TIPO DI VISUALIZZAZIONE
            # ---------------------------------------------------------
            tipo_visualizzazione = st.radio(
                "Seleziona la modalità di visualizzazione del grafico:",
                ["Valori Assoluti (Impilati)", "Percentuale di allocazione Attività (Affiancati per Evento)"],
                horizontal=True
            )
            
            if tipo_visualizzazione == "Percentuale di allocazione Attività (Affiancati per Evento)":
                # Calcoliamo le percentuali per colonna (ogni attività fa 100% in totale sui 3 target)
                pivot_perc = pivot_df.div(pivot_df.sum(axis=0), axis=1) * 100
                
                # Trasponiamo per avere le attività sull'asse Y e i gruppi anagrafica come barre affiancate
                plot_data = pivot_perc.T
                
                # Usiamo i colori coordinati con la torta iniziale per identificare i target (Cliente, Lead, Prospect)
                colors_target = ['#5dade2', '#58d68d', '#ec7063']
                
                fig_bar, ax_bar = plt.subplots(figsize=(12, 8))
                plot_data.plot(kind='barh', stacked=False, ax=ax_bar, color=colors_target, width=0.8)
                
                ax_bar.set_xlabel("Quota di allocazione dell'attività (%)", fontsize=12)
                ax_bar.set_ylabel("Tipo Evento", fontsize=12)
                ax_bar.legend(title="Target Anagrafica", bbox_to_anchor=(1.05, 1), loc='upper left')
                ax_bar.set_xlim(0, 100)
                ax_bar.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}%'))
                
            else:
                # Modalità classica assoluta impilata (Mantiene l'anagrafica sull'asse Y)
                plot_data = pivot_df
                colors_list = [color_mapping_eventi.get(col, '#bdc3c7') for col in plot_data.columns]
                
                fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
                plot_data.plot(kind='barh', stacked=True, ax=ax_bar, color=colors_list)
                
                ax_bar.set_xlabel("Numero di Eventi", fontsize=12)
                ax_bar.set_ylabel("Tipo Anagrafica", fontsize=12)
                ax_bar.legend(title="Tipo Evento", bbox_to_anchor=(1.05, 1), loc='upper left')
            # ---------------------------------------------------------
            
            # Estetica del grafico comune
            ax_bar.set_title("Distribuzione delle attività", fontsize=14, pad=15)
            ax_bar.spines['top'].set_visible(False)
            ax_bar.spines['right'].set_visible(False)
            fig_bar.patch.set_alpha(0)
            
            st.pyplot(fig_bar)
            
        else:
            st.warning("Colonna 'TIPO EVENTO' non trovata. Impossibile mostrare il dettaglio delle attività.")
            
    else:
        st.error(f"Colonna 'TIPO ANAGRAFICA' non trovata. Colonne presenti: {list(df_events.columns)}")
