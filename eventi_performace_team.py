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
