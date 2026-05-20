import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def distribuzione_eventi(df_events):
    """
    Analisi della distribuzione eventi per tipo anagrafica e dettaglio tipo evento.
    Inclusa selezione di filtri specifici per le attività e calcolo delle quote di allocazione.
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
            
            # 1. PULIZIA DATI ALLA FONTE: Rimuoviamo i valori nulli reali prima della conversione
            df_temp = df_temp.dropna(subset=['TIPO EVENTO'])
            
            # Convertiamo tutto rigidamente in stringa pulita
            df_temp['TIPO EVENTO'] = df_temp['TIPO EVENTO'].astype(str).str.strip()
            
            # Rimuoviamo il trattino da 'TELEFONATO -' e le eventuali stringhe 'nan' testuali repentine
            df_temp['TIPO EVENTO'] = df_temp['TIPO EVENTO'].str.replace('TELEFONATO -', 'TELEFONATO', regex=False)
            df_temp = df_temp[df_temp['TIPO EVENTO'] != 'nan']
            
            # ---------------------------------------------------------
            # AGGIUNTA: Filtro Multiselect Attività (Ora sicuro al 100% da TypeError)
            # ---------------------------------------------------------
            elenco_attivita_disponibili = sorted([str(x) for x in df_temp['TIPO EVENTO'].unique()])
            
            attivita_default = [att for att in ['TELEFONATO', 'VISITATO', 'INVIATA MAIL'] if att in elenco_attivita_disponibili]
            
            attivita_selezionate = st.multiselect(
                "Filtra la tipologia di eventi da analizzare nel grafico:",
                options=elenco_attivita_disponibili,
                default=attivita_default
            )
            
            # Applichiamo i filtri (Target Anagrafica + Attività Selezionate)
            df_filtered_types = df_temp[
                (df_temp['TIPO ANAGRAFICA'].isin(target_categories)) & 
                (df_temp['TIPO EVENTO'].isin(attivita_selezionate))
            ]
            # ---------------------------------------------------------
            
            # Controllo di sicurezza nel caso il filtro svuoti i dati
            if df_filtered_types.empty:
                st.warning("Nessun dato disponibile per le attività selezionate.")
                return
            
            # Creiamo la tabella pivot (Crosstab)
            pivot_df = pd.crosstab(df_filtered_types['TIPO ANAGRAFICA'], df_filtered_types['TIPO EVENTO'])
            
            # Reindicizziamo le righe
            pivot_df = pivot_df.reindex(target_categories, fill_value=0)
            pivot_df.index = [idx.capitalize() for idx in pivot_df.index]
            
            # DEFINIZIONE COLORI ACCOPPIATI
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
            
            # SELEZIONE TIPO DI VISUALIZZAZIONE
            tipo_visualizzazione = st.radio(
                "Seleziona la modalità di visualizzazione del grafico:",
                ["Valori Assoluti (Impilati)", "Percentuale di allocazione Attività (Affiancati per Evento)"],
                horizontal=True
            )
            
            if tipo_visualizzazione == "Percentuale di allocazione Attività (Affiancati per Evento)":
                # Calcoliamo le percentuali in verticale (per colonna)
                pivot_perc = pivot_df.div(pivot_df.sum(axis=0), axis=1) * 100
                
                # Trasponiamo per avere le attività sull'asse Y
                plot_data = pivot_perc.T
                
                # Colori target coordinati con la torta iniziale
                colors_target = ['#5dade2', '#58d68d', '#ec7063']
                
                fig_bar, ax_bar = plt.subplots(figsize=(12, 6))
                plot_data.plot(kind='barh', stacked=False, ax=ax_bar, color=colors_target, width=0.7)
                
                ax_bar.set_xlabel("Quota di allocazione dell'attività (%)", fontsize=12)
                ax_bar.set_ylabel("Tipo Evento", fontsize=12)
                ax_bar.legend(title="Target Anagrafica", bbox_to_anchor=(1.05, 1), loc='upper left')
                ax_bar.set_xlim(0, 100)
                ax_bar.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}%'))
                
            else:
                # Modalità classica assoluta impilata
                plot_data = pivot_df
                colors_list = [color_mapping_eventi.get(col, '#bdc3c7') for col in plot_data.columns]
                
                fig_bar, ax_bar = plt.subplots(figsize=(10, 5))
                plot_data.plot(kind='barh', stacked=True, ax=ax_bar, color=colors_list)
                
                ax_bar.set_xlabel("Numero di Eventi", fontsize=12)
                ax_bar.set_ylabel("Tipo Anagrafica", fontsize=12)
                ax_bar.legend(title="Tipo Evento", bbox_to_anchor=(1.05, 1), loc='upper left')
            
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
