import streamlit as st
import pandas as pd
import plotly.express as px

def analisi_performance_utenti(df_events):
    """
    Analisi delle performance del team di utenti/commerciali.
    Mostra due grafici ordinati (Volume con mediana totale e Quota globale con mediane per attività)
    e la tabella analitica finale con formattazione condizionale rispetto alle mediane.
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
        # CALCOLO PIVOT E ORDINAMENTO STRUTTURATO
        # ---------------------------------------------------------
        pivot_base = pd.crosstab(df_filtered[colonna_utente], df_filtered[colonna_evento])
        totale_globale_eventi = pivot_base.sum().sum()
        
        # Creiamo l'ordinamento basato sulla somma totale delle attività per utente
        totale_per_utente = pivot_base.sum(axis=1).sort_values(ascending=False)
        ordine_commerciali_decrescente = list(totale_per_utente.index)
        
        # Trasformiamo i dati nel formato lungo per Plotly
        df_chart = pivot_base.reset_index()
        df_long = df_chart.melt(id_vars=colonna_utente, var_name='Tipo Evento', value_name='Conteggio')
        
        # Calcoliamo le percentuali globali per il secondo grafico
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
        # GRAFICO 1: VOLUME ASSOLUTO (BARRE IMPILATE ORDINATE + LINEA MEDIANA)
        # ---------------------------------------------------------
        st.subheader("1. Volume Assoluto di Attività Svolte dal Team")
        fig_volume = px.bar(
            df_long,
            x=colonna_utente,
            y='Conteggio',
            color='Tipo Evento',
            barmode='relative',
            color_discrete_map=color_mapping_eventi,
            title=f"Totale eventi gestiti per commerciale - Target: {scelta_anagrafica}",
            hover_data=['Tipo Evento'],
            category_orders={colonna_utente: ordine_commerciali_decrescente}
        )
        
        fig_volume.update_traces(
            hovertemplate="<b>Utente: %{x}</b><br>Attività: %{customdata[0]}<br>Quantità: %{y}<extra></extra>"
        )
        
        # NUOVA AGGIUNTA: Calcolo e inserimento della linea di Mediana del volume totale per utente
        mediana_volume_totale = totale_per_utente.median()
        fig_volume.add_hline(
            y=mediana_volume_totale,
            line_dash="dash",
            line_color="#2c3e50",  # Elegante blu scuro/antracite per differenziarsi dalle barre
            line_width=2.5,
            annotation_text=f"Mediana Totale Team: {mediana_volume_totale:.1f}",
            annotation_position="top left",
            annotation_font_color="#2c3e50",
            annotation_font_size=12
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
        # GRAFICO 2: PERCENTUALE SUL TOTALE COMPLESSIVO (BARRE AFFIANCATE + MEDIANE)
        # ---------------------------------------------------------
        st.subheader("2. Impatto del Singolo Commerciale sull'Attività Globale del Team")
        st.caption(f"Le percentuali sono calcolate sul totale di tutti i commerciali uniti (Totale eventi: {totale_globale_eventi})")
        
        fig_percentuale = px.bar(
            df_long,
            x=colonna_utente,
            y='Percentuale Globale',
            color='Tipo Evento',
            barmode='group',
            color_discrete_map=color_mapping_eventi,
            title=f"Quota sul totale delle attività del team - Target: {scelta_anagrafica}",
            hover_data=['Tipo Evento'],
            category_orders={colonna_utente: ordine_commerciali_decrescente}
        )
        
        fig_percentuale.update_traces(
            hovertemplate="<b>Utente: %{x}</b><br>Attività: %{customdata[0]}<br>Quota sul Totale Team: %{y:.1f}%<extra></extra>"
        )
        
        # Calcolo e tracciamento delle mediane per ogni attività sul grafico delle quote
        df_mediane = df_long.groupby('Tipo Evento')['Percentuale Globale'].median().reset_index()
        for _, row in df_mediane.iterrows():
            evento = row['Tipo Evento']
            mediana_val = row['Percentuale Globale']
            colore_linea = color_mapping_eventi.get(evento, '#bdc3c7')
            
            fig_percentuale.add_hline(
                y=mediana_val,
                line_dash="dash",
                line_color=colore_linea,
                line_width=2,
                annotation_text=f"Mediana {evento.capitalize()}: {mediana_val:.1f}%",
                annotation_position="top right",
                annotation_font_color=colore_linea
            )
        
        fig_percentuale.update_layout(
            xaxis_title="Membro del Team",
            yaxis_title="Percentuale sul totale complessivo (%)",
            legend_title="Tipo Evento",
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',
            height=450
        )
        fig_percentuale.update_yaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)', ticksuffix="%")
        st.plotly_chart(fig_percentuale, use_container_width=True)
        
        # ---------------------------------------------------------
        # TABELLA IN FONDO CON FORMATTAZIONE CONDIZIONALE VERDE/ROSSO
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("📋 Registro Performance Team")
        
        if totale_globale_eventi > 0:
            pivot_percentuali = (pivot_base / totale_globale_eventi) * 100
        else:
            pivot_percentuali = pivot_base * 0.0
            
        pivot_percentuali = pivot_percentuali.rename(columns=lambda x: f"{x} (%)")
        pivot_final = pd.concat([pivot_base, pivot_percentuali], axis=1)
        
        pivot_final['TOTALE ATTIVITÀ'] = pivot_base.sum(axis=1)
        if totale_globale_eventi > 0:
            pivot_final['TOTALE COMPLESSIVO (%)'] = (pivot_final['TOTALE ATTIVITÀ'] / totale_globale_eventi) * 100
        else:
            pivot_final['TOTALE COMPLESSIVO (%)'] = 0.0
            
        pivot_final = pivot_final.reindex(ordine_commerciali_decrescente)
        
        colonne_assolute = list(pivot_base.columns) + ['TOTALE ATTIVITÀ']
        colonne_percentuali = list(pivot_percentuali.columns) + ['TOTALE COMPLESSIVO (%)']
        pivot_final = pivot_final[colonne_assolute + colonne_percentuali]
        
        st.write(f"**Tabella Riepilogativa delle Performance ({scelta_anagrafica}):**")
        st.caption("Le celle evidenziate indicano se il commerciale è sopra (🟢) o sotto (🔴) la mediana del team calcolata per quella specifica colonna.")

        # FUNZIONE DI STILE PER LE CELLE DELLA TABELLA (VERDE / ROSSO)
        mediana_totale_compl = pivot_final['TOTALE COMPLESSIVO (%)'].median()
        
        def colora_rispetto_mediana(colonna):
            nome_colonna = colonna.name
            if nome_colonna in colonne_assolute:
                return [''] * len(colonna)
                
            if nome_colonna == 'TOTALE COMPLESSIVO (%)':
                return [
                    'background-color: rgba(46, 204, 113, 0.22); color: #1e8449; font-weight: bold;' if v >= mediana_totale_compl
                    else 'background-color: rgba(231, 76, 60, 0.18); color: #b03a2e;' for v in colonna
                ]
            
            if nome_colonna in pivot_percentuali.columns:
                nome_attività_puro = nome_colonna.replace(" (%)", "")
                mediana_attivita = df_long[df_long['Tipo Evento'] == nome_attività_puro]['Percentuale Globale'].median()
                return [
                    'background-color: rgba(46, 204, 113, 0.22); color: #1e8449;' if v >= mediana_attivita
                    else 'background-color: rgba(231, 76, 60, 0.18); color: #b03a2e;' for v in colonna
                ]
            return [''] * len(colonna)

        # Dizionario di formattazione stringhe per i numeri
        formattazione_stringhe = {
            "TOTALE ATTIVITÀ": "{:.0f}",
            "TOTALE COMPLESSIVO (%)": "{:.1f}%"
        }
        for col in pivot_base.columns:
            formattazione_stringhe[col] = "{:.0f}"
        for col in pivot_percentuali.columns:
            formattazione_stringhe[col] = "{:.1f}%"

        # Generazione ed esposizione della tabella stilizzata
        df_stilizzato = pivot_final.style.apply(colora_rispetto_mediana, axis=0).format(formattazione_stringhe)
        st.dataframe(df_stilizzato, use_container_width=True)
        
    else:
        st.error(f"Colonne richieste non trovate. Assicurati che nel file ci siano 'UTENTE', 'TIPO EVENTO' e 'TIPO ANAGRAFICA'.")
