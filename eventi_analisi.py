import streamlit as st
import pandas as pd
import plotly.express as px

def distribuzione_eventi(df_events):
    """
    Analisi della distribuzione eventi per tipo anagrafica e dettaglio tipo evento.
    Sviluppato con grafici interattivi Plotly (funzione Hover corretta per percentuali e conteggi).
    """
    
    # Verifichiamo che la colonna principale esista
    if 'TIPO ANAGRAFICA' in df_events.columns:
        
        # Numeri eventi per Clienti, Prospect e Lead
        df_temp = df_events.copy()
        counts = df_temp['TIPO ANAGRAFICA'].value_counts()
        target_categories = ['CLIENTE', 'LEAD', 'PROSPECT']
        filtered_counts = counts.reindex(target_categories, fill_value=0).reset_index()
        filtered_counts.columns = ['TIPO ANAGRAFICA', 'CONTEGGIO']
        
        # Formattiamo i nomi per l'estetica della legenda (es. Cliente)
        filtered_counts['Anagrafica'] = filtered_counts['TIPO ANAGRAFICA'].str.capitalize()
        
        totale_eventi = filtered_counts['CONTEGGIO'].sum()
        if totale_eventi > 0:
            filtered_counts['QUOTA'] = (filtered_counts['CONTEGGIO'] / totale_eventi) * 100
        else:
            filtered_counts['QUOTA'] = 0.0
        
        # Layout Streamlit: Colonne per la prima riga (Tabella + Torta Interattiva)
        col1, col2, col3 = st.columns([0.8, 0.1, 1.1])
        
        with col1:
            st.write("**Coinvolgimento per Tipologia Anagrafica:**")
            
            # Prepariamo il dataframe impostando 'Anagrafica' come indice e prendendo Conteggio e Quota
            df_da_mostrare = filtered_counts.set_index('Anagrafica')[['CONTEGGIO', 'QUOTA']]
            
            # Mostriamo il dataframe formattando la colonna QUOTA con il simbolo % e 1 decimale
            st.dataframe(
                df_da_mostrare,
                column_config={
                    "CONTEGGIO": st.column_config.NumberColumn("Eventi", format="%d"),
                    "QUOTA": st.column_config.NumberColumn("Quota (%)", format="%.1f%%")
                },
                use_container_width=True
            )
        
        with col3:
            # Torta Interattiva con Plotly Express
            fig_pie = px.pie(
                filtered_counts, 
                values='CONTEGGIO', 
                names='Anagrafica',
                color='Anagrafica',
                color_discrete_map={'Cliente': '#5dade2', 'Lead': '#58d68d', 'Prospect': '#ec7063'},
                hole=0.3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>%{label}</b><br>Eventi: %{value}<br>Quota: %{percent}")
            fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300, showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        # --- SEZIONE: Dettaglio TIPO EVENTO ---
        if 'TIPO EVENTO' in df_events.columns:
            st.write("**Tipologia Eventi per Anagrafica**")
            
            # Pulizia dati iniziale e messa in sicurezza stringhe
            df_temp['TIPO EVENTO'] = df_temp['TIPO EVENTO'].astype(str).str.strip()
            df_temp['TIPO EVENTO'] = df_temp['TIPO EVENTO'].str.replace('TELEFONATO -', 'TELEFONATO', regex=False)
            df_temp = df_temp[~df_temp['TIPO EVENTO'].isin(['nan', 'None', '', 'NaN'])]
            
            # Pulsante Filtro rapido (Checkbox)
            mostra_solo_principali = st.checkbox(
                "Mostra solo le attività principali (Telefonato, Visitato, Inviata Mail)", 
                value=True
            )
            
            if mostra_solo_principali:
                attivita_da_considerare = ['TELEFONATO', 'VISITATO', 'INVIATA MAIL']
                df_filtered_types = df_temp[
                    (df_temp['TIPO ANAGRAFICA'].isin(target_categories)) & 
                    (df_temp['TIPO EVENTO'].isin(attivita_da_considerare))
                ]
            else:
                df_filtered_types = df_temp[df_temp['TIPO ANAGRAFICA'].isin(target_categories)]
            
            if df_filtered_types.empty:
                st.warning("Nessun dato disponibile con i filtri selezionati.")
                return
            
            # Creiamo la tabella pivot (Crosstab) di base
            pivot_df = pd.crosstab(df_filtered_types['TIPO ANAGRAFICA'], df_filtered_types['TIPO EVENTO'])
            pivot_df = pivot_df.reindex(target_categories, fill_value=0)
            pivot_df.index = [idx.capitalize() for idx in pivot_df.index]
            
            # Mappa Colori Custom
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
                # Calcolo percentuali verticali
                pivot_perc = pivot_df.div(pivot_df.sum(axis=0), axis=1) * 100
                
                df_long = pivot_perc.T.reset_index()
                df_long = df_long.melt(id_vars='TIPO EVENTO', var_name='Target Anagrafica', value_name='Percentuale')
                
                # Grafico BARRE AFFIANCATE con Plotly
                fig_bar = px.bar(
                    df_long,
                    y='TIPO EVENTO',
                    x='Percentuale',
                    color='Target Anagrafica',
                    barmode='group',
                    orientation='h',
                    color_discrete_map={'Cliente': '#5dade2', 'Lead': '#58d68d', 'Prospect': '#ec7063'},
                    title="Ripartizione percentuale di ogni attività sui Target"
                )
                
                # RISOLTO: Configurazione hover stringendo il legame con le variabili di df_long
                fig_bar.update_traces(
                    hovertemplate="<b>Attività: %{y}</b><br>Target: %{legendgroup}<br>Quota di allocazione: %{x:.1f}%<extra></extra>"
                )
                fig_bar.update_layout(xaxis_title="Percentuale di allocazione (%)")
                fig_bar.update_xaxes(ticksuffix="%")
                
            else:
                # Modalità classica assoluta impilata
                df_long = pivot_df.reset_index()
                df_long = df_long.melt(id_vars='index', var_name='Tipo Evento', value_name='Conteggio')
                df_long.columns = ['Tipo Anagrafica', 'Tipo Evento', 'Conteggio']
                
                # Grafico BARRE IMPILATE con Plotly
                fig_bar = px.bar(
                    df_long,
                    y='Tipo Anagrafica',
                    x='Conteggio',
                    color='Tipo Evento',
                    barmode='relative',
                    orientation='h',
                    color_discrete_map=color_mapping_eventi,
                    title="Volume Assoluto Attività svolte per Target"
                )
                
                # RISOLTO: Mappatura pulita per il grafico a barre impilate
                fig_bar.update_traces(
                    hovertemplate="<b>Target Anagrafica: %{y}</b><br>Attività: %{legendgroup}<br>Quantità eventi: %{x}<extra></extra>"
                )
                fig_bar.update_layout(xaxis_title="Numero di Eventi")
            
            # Regolazioni di estetica comuni per Plotly
            fig_bar.update_layout(
                yaxis_title="",
                legend_title="Legenda",
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',  
                height=450
            )
            fig_bar.update_xaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)')
            
            # Renderizziamo in Streamlit
            st.plotly_chart(fig_bar, use_container_width=True)
            
        else:
            st.warning("Colonna 'TIPO EVENTO' non trouvée. Impossibile mostrare il dettaglio delle attività.")
            
    else:
        st.error(f"Colonna 'TIPO ANAGRAFICA' non trovata. Colonne presenti: {list(df_events.columns)}")
