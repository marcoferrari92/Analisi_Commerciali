import streamlit as st
import pandas as pd
import plotly.express as px

def analisi_performance_utenti(df_events):
    """
    Analisi delle performance del team di utenti/commerciali.
    Mostra i volumi assoluti, il mix di attività in percentuale sul singolo utente
    e il registro analitico con formattazione condizionale rispetto alle mediane di colonna.
    """
    colonna_utente = 'UTENTE'
    colonna_evento = 'TIPO EVENTO'
    colonna_anagrafica = 'TIPO ANAGRAFICA'
    
    if colonna_utente in df_events.columns and colonna_evento in df_events.columns:
        st.markdown("## Performance del Team")
        
        # 1. PULIZIA DATI ALLA FONTE
        df_temp = df_events.copy()
        df_temp[colonna_evento] = df_temp[colonna_evento].astype(str).str.strip()
        df_temp[colonna_evento] = df_temp[colonna_evento].str.replace('TELEFONATO -', 'TELEFONATO', regex=False)
        df_temp[colonna_utente] = df_temp[colonna_utente].astype(str).str.strip()
        
        if colonna_anagrafica in df_temp.columns:
            df_temp[colonna_anagrafica] = df_temp[colonna_anagrafica].astype(str).str.upper().str.strip()
        
        df_temp = df_temp[~df_temp[colonna_evento].isin(['nan', 'None', '', 'NaN'])]
        df_temp = df_temp[~df_temp[colonna_utente].isin(['nan', 'None', '', 'NaN'])]
        
        # FILTRO: Selezione Target Anagrafica
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
        
        # FILTRI SECONDARI
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
        # COSTRUZIONE MATRICE DI BASE (TABELLA PIVOT)
        # ---------------------------------------------------------
        # Riempiamo i vuoti con 0 per garantire la consistenza statistica dei calcoli
        pivot_base = pd.crosstab(df_filtered[colonna_utente], df_filtered[colonna_evento]).fillna(0)
        
        # Ordinamento basato sulla somma totale delle attività per utente
        totale_per_utente = pivot_base.sum(axis=1).sort_values(ascending=False)
        ordine_commerciali_decrescente = list(totale_per_utente.index)
        pivot_base = pivot_base.reindex(ordine_commerciali_decrescente)
        
        # Formato lungo per Plotly
        df_long = pivot_base.reset_index().melt(id_vars=colonna_utente, var_name='Tipo Evento', value_name='Conteggio')
        
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
        # GRAFICO 1: VOLUME ASSOLUTO
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
            category_orders={colonna_utente: ordine_commerciali_decrescente}
        )
        
        fig_volume.update_traces(
            hovertemplate="<b>Utente: %{x}</b><br>Attività: %{customdata[0]}<br>Quantità: %{y}<extra></extra>",
            customdata=df_long[['Tipo Evento']]
        )
        
        # Mediana del volume totale per utente
        mediana_volume_totale = totale_per_utente.median()
        fig_volume.add_hline(
            y=mediana_volume_totale,
            line_dash="dash",
            line_color="#2c3e50",
            line_width=2.5,
            annotation_text=f"Mediana Team: {mediana_volume_totale:.1f}",
            annotation_position="top right",
            annotation_font_color="#2c3e50",
            annotation_font_size=12
        )
        
        fig_volume.update_layout(
            xaxis_title="Membro del Team", yaxis_title="Numero di Attività",
            legend_title="Tipo Evento", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400
        )
        fig_volume.update_yaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)')
        st.plotly_chart(fig_volume, use_container_width=True)
        
        # ---------------------------------------------------------
        # GRAFICO 2: MIX PERCENTUALE (100% STACKED BAR)
        # ---------------------------------------------------------
        st.subheader("2. Bilanciamento e Mix delle Attività per Singolo Commerciale")
        st.caption("Mostra la ripartizione percentuale delle attività sul totale di ciascun commerciale.")
        
        # Calcoliamo la percentuale normalizzata sul singolo utente (somma orizzontale = 100%)
        df_long_perc = df_long.copy()
        totati_mappa = df_long_perc.groupby(colonna_utente)['Conteggio'].transform('sum')
        df_long_perc['Percentuale Utente'] = (df_long_perc['Conteggio'] / totati_mappa * 100).fillna(0)

        fig_percentuale = px.bar(
            df_long_perc,
            x=colonna_utente,
            y='Percentuale Utente',
            color='Tipo Evento',
            barmode='relative', # Genera un perfetto grafico 100% stacked
            color_discrete_map=color_mapping_eventi,
            title=f"Mix strategico delle attività - Target: {scelta_anagrafica}",
            category_orders={colonna_utente: ordine_commerciali_decrescente}
        )
        
        fig_percentuale.update_traces(
            hovertemplate="<b>Utente: %{x}</b><br>Attività: %{customdata[0]}<br>Quota sul suo totale: %{y:.1f}%<extra></extra>",
            customdata=df_long_perc[['Tipo Evento']]
        )
        
        fig_percentuale.update_layout(
            xaxis_title="Membro del Team", yaxis_title="Quota sul totale del singolo commerciale (%)",
            legend_title="Tipo Evento", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400
        )
        fig_percentuale.update_yaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)', ticksuffix="%")
        st.plotly_chart(fig_percentuale, use_container_width=True)
        
        # ---------------------------------------------------------
        # TABELLA RIASSUNTIVA CON MEDIANE CORRETTE PER COLONNA
        # ---------------------------------------------------------
        st.subheader("📋 Registro Performance Team")
        
        # Costruiamo la tabella finale partendo dai dati assoluti
        pivot_final = pivot_base.copy()
        pivot_final['TOTALE ATTIVITÀ'] = totale_per_utente
        
        # Aggiungiamo le colonne percentuali calcolate sulla specifica attività del TEAM (verticale)
        totale_team_per_attivita = pivot_base.sum(axis=0)
        totale_globale_inter_team = totale_team_per_attivita.sum()
        
        for col in pivot_base.columns:
            tot_att = totale_team_per_attivita[col]
            pivot_final[f"{col} (%)"] = (pivot_base[col] / tot_att * 100).fillna(0) if tot_att > 0 else 0.0
            
        pivot_final['TOTALE COMPLESSIVO (%)'] = (pivot_final['TOTALE ATTIVITÀ'] / totale_globale_inter_team * 100).fillna(0) if totale_globale_inter_team > 0 else 0.0
        
        colonne_assolute = list(pivot_base.columns) + ['TOTALE ATTIVITÀ']
        colonne_percentuali = [f"{c} (%)" for c in pivot_base.columns] + ['TOTALE COMPLESSIVO (%)']
        pivot_final = pivot_final[colonne_assolute + colonne_percentuali]
        
        st.write(f"**Tabella Riepilogativa delle Performance ({scelta_anagrafica}):**")
        st.caption("Le celle evidenziate indicano se il commerciale ha performato sopra (🟢) o sotto (🔴) la **mediana effettiva del team** per quella specifica voce.")

        # FUNZIONE DI STILE MATRICIALE CORRETTA
        def colora_rispetto_mediana_v2(df_da_stilizzare):
            # Creiamo un dataframe di stili vuoti con la stessa struttura
            stili = pd.DataFrame('', index=df_da_stilizzare.index, columns=df_da_stilizzare.columns)
            
            # 1. Colora il TOTALE COMPLESSIVO (%) basandosi sulla sua mediana di colonna
            mediana_tot = df_da_stilizzare['TOTALE COMPLESSIVO (%)'].median()
            stili['TOTALE COMPLESSIVO (%)'] = [
                'background-color: rgba(46, 204, 113, 0.22); color: #1e8449; font-weight: bold;' if v >= mediana_tot
                else 'background-color: rgba(231, 76, 60, 0.18); color: #b03a2e;' for v in df_da_stilizzare['TOTALE COMPLESSIVO (%)']
            ]
            
            # 2. Colora le singole colonne percentuali basandosi sulla loro rispettiva mediana di colonna
            for col in colonne_percentuali[:-1]: # Escludiamo il totale complessivo appena fatto
                mediana_colonna = df_da_stilizzare[col].median()
                stili[col] = [
                    'background-color: rgba(46, 204, 113, 0.22); color: #1e8449;' if v >= mediana_colonna
                    else 'background-color: rgba(231, 76, 60, 0.18); color: #b03a2e;' for v in df_da_stilizzare[col]
                ]
                
            return stili

        # Dizionario di formattazione stringhe dinamico
        formattazione_stringhe = {col: "{:.0f}" for col in colonne_assolute}
        formattazione_stringhe.update({col: "{:.1f}%" for col in colonne_percentuali})

        # Generazione ed esposizione della tabella stilizzata
        df_stilizzato = pivot_final.style.apply(colora_rispetto_mediana_v2, axis=None).format(formattazione_stringhe)
        st.dataframe(df_stilizzato, use_container_width=True)
        
    else:
        st.error("Colonne richieste non trovate. Assicurati che nel file ci siano 'UTENTE', 'TIPO EVENTO' e 'TIPO ANAGRAFICA'.")
