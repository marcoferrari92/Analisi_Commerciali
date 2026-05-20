import streamlit as st
import pandas as pd
import plotly.express as px

def distribuzione_eventi(df_events):
    """
    Analisi della distribuzione eventi per tipo anagrafica e dttaglio tipo evento.
    Sviluppato con grafici interattivi Plotly (Hover ed etichette corrette al 100%).
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
            st.write("**Coinvolgimento per Tipologia Anagrafica**")
            st.write("")
            st.write("")
            df_da_mostrare = filtered_counts.set_index('Anagrafica')[['CONTEGGIO', 'QUOTA']]
            st.dataframe(
                df_da_mostrare,
                column_config={
                    "CONTEGGIO": st.column_config.NumberColumn("Eventi", format="%d"),
                    "QUOTA": st.column_config.NumberColumn("Quota (%)", format="%.1f%%")
                },
                use_container_width=True
            )
        
        with col3:
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
            
            # Mappa Colori Custom per la modalità assoluta
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
                
                # Grafico BARRE AFFIANCATE
                fig_bar = px.bar(
                    df_long,
                    y='TIPO EVENTO',
                    x='Percentuale',
                    color='Target Anagrafica',
                    barmode='group',
                    orientation='h',
                    color_discrete_map={'Cliente': '#5dade2', 'Lead': '#58d68d', 'Prospect': '#ec7063'},
                    title="Ripartizione Anagrafiche per Attività",
                    hover_data=['Target Anagrafica'] # Forziamo il passaggio della colonna corretta a customdata
                )
                
                # RISOLTO: Mappatura robusta basata sull'array customdata
                fig_bar.update_traces(
                    hovertemplate="<b>Attività: %{y}</b><br>Target: %{customdata[0]}<br>Quota di allocazione: %{x:.1f}%<extra></extra>"
                )
                fig_bar.update_layout(xaxis_title="Percentuale di allocazione (%)")
                fig_bar.update_xaxes(ticksuffix="%")
                
            else:
                # Modalità classica assoluta impilata
                df_long = pivot_df.reset_index()
                df_long = df_long.melt(id_vars='index', var_name='Tipo Evento', value_name='Conteggio')
                df_long.columns = ['Tipo Anagrafica', 'Tipo Evento', 'Conteggio']
                
                # Grafico BARRE IMPILATE
                fig_bar = px.bar(
                    df_long,
                    y='Tipo Anagrafica',
                    x='Conteggio',
                    color='Tipo Evento',
                    barmode='relative',
                    orientation='h',
                    color_discrete_map=color_mapping_eventi,
                    title="Volume Attività per Anagrafica",
                    hover_data=['Tipo Evento'] # Forziamo il passaggio della colonna corretta a customdata
                )
                
                # RISOLTO: Mappatura robusta basata sull'array customdata
                fig_bar.update_traces(
                    hovertemplate="<b>Target Anagrafica: %{y}</b><br>Attività: %{customdata[0]}<br>Quantità eventi: %{x}<extra></extra>"
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
            
            st.plotly_chart(fig_bar, use_container_width=True)
            
        else:
            st.warning("Colonna 'TIPO EVENTO' non trovata. Impossibile mostrare il dettaglio delle attività.")
            
    else:
        st.error(f"Colonna 'TIPO ANAGRAFICA' non trovata. Colonne presenti: {list(df_events.columns)}")







import streamlit as st
import pandas as pd
import plotly.express as px

def analisi_performance_utenti(df_events):
    """
    Analisi delle performance del team di utenti/commerciali.
    Mostra due grafici: uno per volumi assoluti impilati e uno per percentuali sul totale globale.
    """
    colonna_utente = 'UTENTE'
    colonna_evento = 'TIPO EVENTO'
    colonna_anagrafica = 'TIPO ANAGRAFICA'
    
    # Verifichiamo che le colonne necessarie esistano nel dataset
    if colonna_utente in df_events.columns and colonna_evento in df_events.columns:
        st.markdown("## 📊 Performance del Team Utenti")
        
        # 1. PULIZIA DATI ALLA FONTE
        df_temp = df_events.copy()
        df_temp[colonna_evento] = df_temp[colonna_evento].astype(str).str.strip()
        df_temp[colonna_evento] = df_temp[colonna_evento].str.replace('TELEFONATO -', 'TELEFONATO', regex=False)
        df_temp[colonna_utente] = df_temp[colonna_utente].astype(str).str.strip()
        
        if colonna_anagrafica in df_temp.columns:
            df_temp[colonna_anagrafica] = df_temp[colonna_anagrafica].astype(str).str.upper().str.strip()
        
        # Rimuoviamo i valori nulli o spuri
        df_temp = df_temp[~df_temp[colonna_evento].isin(['nan', 'None', '', 'NaN'])]
        df_temp = df_temp[~df_temp[colonna_utente].isin(['nan', 'None', '', 'NaN'])]
        
        # ---------------------------------------------------------
        # FILTRO: Selezione Target Anagrafica
        # ---------------------------------------------------------
        scelta_anagrafica = st.selectbox(
            "Seleziona il target di anagrafica da analizzare:",
            ["Tutte le anagrafiche", "Clienti", "Lead", "Prospect"]
        )
        
        if scelta_anagrafica == "Clienti":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'CLIENTE']
        elif scelta_anagrafica == "Lead":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'LEAD']
        elif scelta_anagrafica == "Prospect":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'PROSPECT']
        
        # FILTRI SECONDARI (Attività + Selezione Utenti)
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            mostra_solo_principali = st.checkbox(
                "Mostra solo attività principali (Telefonato, Visitato, Inviata Mail)", 
                value=True,
                key="utenti_filtro_attivita"
            )
            if mostra_solo_principali:
                attivita_target = ['TELEFONATO', 'VISITATO', 'INVIATA MAIL']
                df_temp = df_temp[df_temp[colonna_evento].isin(attivita_target)]
        
        with col_f2:
            elenco_utenti = sorted(df_temp[colonna_utente].unique())
            utenti_selezionati = st.multiselect(
                "Filtra o isola utenti specifici:",
                options=elenco_utenti,
                default=elenco_utenti,
                key="utenti_filtro_nomi"
            )
            df_filtered = df_temp[df_temp[colonna_utente].isin(utenti_selezionati)]
            
        if df_filtered.empty:
            st.warning("Nessun dato disponibile con i filtri selezionati.")
            return
            
        # ---------------------------------------------------------
        # TABELLA RIASSUNTIVA DELLE CLASSIFICHE
        # ---------------------------------------------------------
        st.markdown("---")
        
        # Creiamo la tabella Pivot (Righe: Utenti, Colonne: Attività)
        pivot_utenti = pd.crosstab(df_filtered[colonna_utente], df_filtered[colonna_evento])
        
        # Calcoliamo il totale complessivo per utente per fare la classifica ordinata
        pivot_utenti['TOTALE ATTIVITÀ'] = pivot_utenti.sum(axis=1)
        pivot_utenti = pivot_utenti.sort_values(by='TOTALE ATTIVITÀ', ascending=False)
        
        st.write(f"**Riepilogo Attività per Utente ({scelta_anagrafica}):**")
        st.dataframe(pivot_utenti, use_container_width=True)
        
        # ---------------------------------------------------------
        # PREPARAZIONE DATI PER I GRAFICI (Melt in formato lungo)
        # ---------------------------------------------------------
        df_chart = pivot_utenti.drop(columns=['TOTALE ATTIVITÀ']).reset_index()
        df_long = df_chart.melt(id_vars=colonna_utente, var_name='Tipo Evento', value_name='Conteggio')
        
        # Calcolo del Totale Globale di tutti gli eventi filtrati (Tutti i commerciali insieme)
        totale_globale_eventi = df_long['Conteggio'].sum()
        
        # Calcoliamo la percentuale sul totale complessivo del team
        if totale_globale_eventi > 0:
            df_long['Percentuale Globale'] = (df_long['Conteggio'] / totale_globale_eventi) * 100
        else:
            df_long['Percentuale Globale'] = 0.0
            
        # Palette Colori Coerente
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
        
        st.markdown("---")
        
        # ---------------------------------------------------------
        # GRAFICO 1: VOLUME ASSOLUTO (BARRE IMPILATE)
        # ---------------------------------------------------------
        st.subheader("1. Volume Assoluto di Attività Svolte")
        fig_volume = px.bar(
            df_long,
            x=colonna_utente,
            y='Conteggio',
            color='Tipo Evento',
            barmode='relative', # Impilate una sull'altra
            color_discrete_map=color_mapping_eventi,
            title=f"Totale eventi gestiti per commerciale - Target: {scelta_anagrafica}",
            hover_data=['Tipo Evento']
        )
        
        fig_volume.update_traces(
            hovertemplate="<b>Utente: %{x}</b><br>Attività: %{customdata[0]}<br>Quantità: %{y}<extra></extra>"
        )
        
        fig_volume.update_layout(
            xaxis_title="Membro del Team",
            yaxis_title="Numero di Attività",
            legend_title="Tipo Evento",
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        fig_volume.update_yaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)')
        st.plotly_chart(fig_volume, use_container_width=True)
        
        # ---------------------------------------------------------
        # GRAFICO 2: PERCENTUALE SUL TOTALE COMPLESSIVO (BARRE IMPILATE O AFFIANCATE)
        # ---------------------------------------------------------
        st.subheader("2. Impatto Percentuale sul Totale Globale del Team")
        st.caption(f"Le percentuali sono calcolate sul totale di tutti i commerciali uniti (Totale eventi: {totale_globale_eventi})")
        
        fig_percentuale = px.bar(
            df_long,
            x=colonna_utente,
            y='Percentuale Globale',
            color='Tipo Evento',
            barmode='relative', # Mantengo impilato così vedi la quota totale del commerciale sull'azienda
            color_discrete_map=color_mapping_eventi,
            title=f"Quota di contribuzione sul totale delle attività del team (%)",
            hover_data=['Tipo Evento']
        )
        
        fig_percentuale.update_traces(
            hovertemplate="<b>Utente: %{x}</b><br>Attività: %{customdata[0]}<br>Quota sul Totale Team: %{y:.1f}%<extra></extra>"
        )
        
        fig_percentuale.update_layout(
            xaxis_title="Membro del Team",
            yaxis_title="Percentuale sul totale complessivo (%)",
            legend_title="Tipo Evento",
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        fig_percentuale.update_yaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)', ticksuffix="%")
        st.plotly_chart(fig_percentuale, use_container_width=True)
        
    else:
        st.error(f"Colonne richieste non trovate. Assicurati che nel file ci siano 'UTENTE', 'TIPO EVENTO' e 'TIPO ANAGRAFICA'.")
