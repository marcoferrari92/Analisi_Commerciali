import streamlit as st
import pandas as pd
import plotly.express as px

def coinvolgimento_aziende(df_events):
    """
    Analisi del coinvolgimento delle aziende lato eventi.
    Layout riorganizzato:
    1. Grafico Attività Medie per Azienda + Mediana
    2. Mappa Treemap delle Top Aziende
    3. Tabella Pivot di ripartizione attività
    4. Registro analitico finale degli eventi
    """
    colonna_utente = 'UTENTE'
    colonna_evento = 'TIPO EVENTO'
    colonna_anagrafica = 'TIPO ANAGRAFICA'
    colonna_ragione_sociale = 'RAGIONE SOCIALE'
    
    # Verifichiamo la presenza delle colonne minime necessarie
    if colonna_ragione_sociale in df_events.columns and colonna_utente in df_events.columns:
        st.write("")
        st.markdown("## Analisi Coinvolgimento Aziende")
        st.write("")
        st.write("")
        
        # Copia di sicurezza per non sporcare il dataframe originale
        df_temp = df_events.copy()
        
        # ---------------------------------------------------------
        # FILTRO: Selezione Target Anagrafica
        # ---------------------------------------------------------
        scelta_anagrafica = st.selectbox(
            "Seleziona il target di anagrafica aziende da analizzare:",
            ["Tutte le anagrafiche", "Clienti", "Lead", "Prospect"],
            key="aziende_filtro_anagrafica"
        )
        
        if scelta_anagrafica == "Clienti":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'CLIENTE']
        elif scelta_anagrafica == "Lead":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'LEAD']
        elif scelta_anagrafica == "Prospect":
            df_temp = df_temp[df_temp[colonna_anagrafica] == 'PROSPECT']
            
        if df_temp.empty:
            st.warning(f"Nessun dato disponibile per la categoria selezionata: {scelta_anagrafica}")
            return

        st.markdown("---")

        # ---------------------------------------------------------
        # 1. PRIMA COSA: GRAFICO DEL COINVOLGIMENTO MEDIO PER AZIENDA
        # ---------------------------------------------------------
        st.write(f"#### Numero Medio di Attività per Azienda - {scelta_anagrafica}")
        
        # Calcoliamo per ogni utente il numero di attività totali e il numero di aziende uniche gestite
        df_metrics_utenti = df_temp.groupby(colonna_utente).agg(
            Attivita_Totali=('TIPO EVENTO', 'count'),
            Aziende_Uniche=(colonna_ragione_sociale, 'nunique')
        ).reset_index()
        
        # Calcolo della media per azienda
        df_metrics_utenti['Attività Medie'] = (df_metrics_utenti['Attivita_Totali'] / df_metrics_utenti['Aziende_Uniche']).round(1)
        
        # Ordiniamo dal minore al maggiore per Plotly (l'asse y cresce dal basso verso l'alto)
        stats_utenti = df_metrics_utenti.sort_values(by='Attività Medie', ascending=True)
        
        if not stats_utenti.empty:
            valore_mediana = stats_utenti['Attività Medie'].median()
            
            fig_bar = px.bar(
                stats_utenti, 
                x='Attività Medie', 
                y=colonna_utente, 
                orientation='h', 
                text='Attività Medie',
                color='Attività Medie', 
                color_continuous_scale='Blues',
                hover_data={'Attivita_Totali': True, 'Aziende_Uniche': True}
            )
            
            fig_bar.update_traces(
                hovertemplate="<b>Commerciale: %{y}</b><br>Media Attività/Azienda: %{x}<br>Azioni Totali: %{customdata[0]}<br>Aziende Gestite: %{customdata[1]}<extra></extra>"
            )
            
            fig_bar.add_vline(
                x=valore_mediana, 
                line_dash="dash", 
                line_color="red",
                line_width=2,
                annotation_text=f"Mediana Team: {valore_mediana:.1f}", 
                annotation_position="top right"
            )
            
            fig_bar.update_layout(
                xaxis_title="Media Attività per Azienda (N. Azioni / N. Aziende)",
                yaxis_title="Commerciale",
                showlegend=False,
                height=400,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            fig_bar.update_xaxes(showgrid=True, gridcolor='rgba(200,200,200,0.2)')
            
            st.plotly_chart(fig_bar, use_container_width=True)
            st.metric(f"Mediana Attività/Azienda del Team ({scelta_anagrafica})", f"{valore_mediana:.1f} azioni")
        
        st.markdown("---")

        # ---------------------------------------------------------
        # 2. SOTTO IL BARCHART: MAPPA AD ALBERO (TREEMAP)
        # ---------------------------------------------------------
        st.write(f"#### Top Aziende per Commerciale - {scelta_anagrafica}")
        
        # Troviamo per ogni azienda chi è il commerciale che ha fatto più attività
        df_top_comm = df_temp.groupby([colonna_ragione_sociale, colonna_utente]).size().reset_index(name='Conteggio')
        
        # Per ogni azienda, prendiamo solo la riga del commerciale con il conteggio massimo
        df_color = df_top_comm.sort_values('Conteggio', ascending=False).drop_duplicates(colonna_ragione_sociale)
        df_color = df_color[[colonna_ragione_sociale, colonna_utente]]
        df_color.columns = ['Azienda', 'Commerciale Prevalente']
        
        # Uniamo con i totali per azienda
        stats_aziende = df_temp[colonna_ragione_sociale].value_counts().reset_index()
        stats_aziende.columns = ['Azienda', 'Numero Attività']
        
        # Prendiamo le prime 50 aziende per non sovraccaricare il grafico
        df_tree = pd.merge(stats_aziende.head(50), df_color, on='Azienda')
        
        if not df_tree.empty:
            fig_tree = px.treemap(
                df_tree, 
                path=['Commerciale Prevalente', 'Azienda'], 
                values='Numero Attività',
                color='Numero Attività',
                color_continuous_scale='Blues',
                height=600
            )
            
            fig_tree.update_traces(
                textinfo="label+value",
                texttemplate="<b>%{label}</b><br>Attività: %{value}",
                hovertemplate="<b>%{label}</b><br>TOTALE: %{value}",
                insidetextfont=dict(size=14),
                textposition="middle center"
            )
            
            fig_tree.update_layout(
                margin=dict(t=80, l=10, r=10, b=10),
                coloraxis_colorbar=dict(
                    title="Intensità Attività",
                    thicknessmode="pixels", thickness=15,
                    lenmode="fraction", len=0.5,
                    yanchor="top", y=1.12,
                    xanchor="center", x=0.5,
                    orientation="h"
                )
            )
            st.plotly_chart(fig_tree, use_container_width=True)
        else:
            st.info("Dati insufficienti per generare la mappa ad albero.")

        # ---------------------------------------------------------
        # 3. SOTTO IL TREE: TABELLA PIVOT CON IL DETTAGLIO ATTIVITÀ
        # ---------------------------------------------------------
        st.write("#### Dettaglio Attività per Azienda")
        
        pivot_aziende = df_temp.pivot_table(
            index=colonna_ragione_sociale, 
            columns=colonna_evento, 
            values=colonna_utente, 
            aggfunc='count', 
            fill_value=0
        ).reset_index()
        
        colonne_attivita = [c for c in pivot_aziende.columns if c != colonna_ragione_sociale]
        pivot_aziende['TOTALE'] = pivot_aziende[colonne_attivita].sum(axis=1)
        
        comm_riferimento = df_temp.groupby(colonna_ragione_sociale)[colonna_utente].unique().apply(lambda x: ", ".join(x)).reset_index()
        comm_riferimento.columns = [colonna_ragione_sociale, 'Commerciali']
        
        df_finale_aziende = pd.merge(pivot_aziende, comm_riferimento, on=colonna_ragione_sociale)
        cols = [colonna_ragione_sociale, 'TOTALE'] + list(colonne_attivita) + ['Commerciali']
        df_finale_aziende = df_finale_aziende[cols].sort_values(by='TOTALE', ascending=False)
        
        st.dataframe(df_finale_aziende, hide_index=True, use_container_width=True)

        st.markdown("---")

        # ---------------------------------------------------------
        # 4. PER ULTIMO: IL REGISTRO CRONOLOGICO
        # ---------------------------------------------------------
        st.write(f"### Dettaglio eventi estratti ({len(df_temp)} record)")
        col_view = ['UTENTE', 'DATA', 'ORA EVENTO', 'TIPO EVENTO', colonna_ragione_sociale, 'NOTE']
        col_presenti = [c for c in col_view if c in df_temp.columns]
        
        st.dataframe(
            df_temp[col_presenti].sort_values(by=['DATA', 'ORA EVENTO'], ascending=[False, False]),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.error(f"Colonne richieste non trovate. Assicurati che nel file ci siano 'RAGIONE SOCIALE' e 'UTENTE'.")
