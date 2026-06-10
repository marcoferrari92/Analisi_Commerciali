import streamlit as st
import pandas as pd
import re

def elabora_gestionale(df_input):
    """
    Prende il dataframe del gestionale, unisce le catene a 3 livelli e gestisce le decurtazioni (CHPR ORD XX)
    associando la terna (SEZIONALE, NUMERO, ID_CLIENTI). Imposta correttamente l'ID dell'ordine padre trovato
    all'interno della colonna ID_DOCUMENTO_PADRE, mantenendo intatto l'ID originale della decurtazione.
    """
    # --- 0. PULSANTE DI REFRESH IN CIMA ALLA PAGINA ---
    if st.button("🔄 Forza Ricaricamento Dati e Reset", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # 1. COPIA E PREPARAZIONE DATI
    df = df_input.copy()
    df['TIPO_DOCUMENTO'] = df['TIPO_DOCUMENTO'].astype(str).str.strip().str.upper()
    
    # Conversione forzata in numeri interi
    if 'QT' in df.columns:
        df['QT'] = pd.to_numeric(df['QT'], errors='coerce').fillna(0).astype(int)
    if 'NUMERO' in df.columns:
        df['NUMERO'] = pd.to_numeric(df['NUMERO'], errors='coerce').fillna(0).astype(int)
    if 'SEZIONALE' in df.columns:
        df['SEZIONALE'] = pd.to_numeric(df['SEZIONALE'], errors='coerce').fillna(0).astype(int)
    if 'ID_CLIENTI' in df.columns:
        df['ID_CLIENTI'] = pd.to_numeric(df['ID_CLIENTI'], errors='coerce').fillna(0).astype(int)

   # --- 2. DIZIONARI DI MAPPATURA GLOBALI ---
    # Pre-calcoliamo le mappe prima di definire la funzione per evitare NameError
    mappa_terna_a_id = df.drop_duplicates('ID_DOCUMENTI').set_index(['SEZIONALE', 'NUMERO', 'ID_CLIENTI'])['ID_DOCUMENTI'].to_dict()
    # Mappa di fallback: (NUMERO, ID_CLIENTI) -> ID_DOCUMENTI
    mappa_fallback = df.groupby(['NUMERO', 'ID_CLIENTI'])['ID_DOCUMENTI'].first().to_dict()

    # --- 2.1 AGGIORNAMENTO DI ID_DOCUMENTO_PADRE PER LE DECURTAZIONI CHIUSE ---
    def assegna_id_padre_a_chpr(row):

        padre_orig  = row['ID_DOCUMENTO_PADRE']
        titolo      = str(row['TITOLO']).upper()
        id_cliente  = int(row['ID_CLIENTI'])
        sezionale   = int(row['SEZIONALE'])
        
        if 'CHPR' in titolo:
            match_numero = re.search(r'\d+', titolo)
            if match_numero:
                numero_target = int(match_numero.group())
                
                # STEP 1: Tentativo con terna completa (Preciso)
                id_ordine = mappa_terna_a_id.get((sezionale, numero_target, id_cliente))
                
                # STEP 2: Fallback (solo numero e cliente) se la terna fallisce
                if id_ordine is None:
                    id_ordine = mappa_fallback.get((numero_target, id_cliente))
                
                if id_ordine is not None:
                    return id_ordine
                    
        return padre_orig

    # Applichiamo la funzione (ora che le mappe sono definite nello scope superiore)
    df['ID_DOCUMENTO_PADRE'] = df.apply(assegna_id_padre_a_chpr, axis=1)


    # 2.1 AGGIORNAMENTO DI ID_DOCUMENTO_PADRE PER LE DECURTAZIONI CHIUSE

    # --- AGGIUNTA FONDAMENTALE ---
    # Questa mappa deve esistere PRIMA di definire calcola_revisione
    mappa_padri = df.set_index('ID_DOCUMENTI')['ID_DOCUMENTO_PADRE'].to_dict()

    # 2.2 LOGICA CALCOLO REVISIONI
    mappa_tipi = df.set_index('ID_DOCUMENTI')['TIPO_DOCUMENTO'].to_dict()
    
    # Pre-calcoliamo chi è figlio di chi per velocizzare
    figli_dict = df.groupby('ID_DOCUMENTO_PADRE')['ID_DOCUMENTI'].apply(list).to_dict()

    def calcola_revisione(row):
        id_doc = row['ID_DOCUMENTI']
        # Ora mappa_padri è definita nel flusso e accessibile qui
        padre = mappa_padri.get(id_doc) 
        tipo_corrente = row['TIPO_DOCUMENTO']
        
        ha_figli_stesso_tipo = False
        if id_doc in figli_dict:
            for figlio_id in figli_dict[id_doc]:
                if mappa_tipi.get(figlio_id) == tipo_corrente:
                    ha_figli_stesso_tipo = True
                    break
        
        profondita = 0
        corrente = id_doc
        while True:
            # mappa_padri è ora definita correttamente
            id_padre = mappa_padri.get(corrente)
            if id_padre and id_padre in mappa_tipi and mappa_tipi[id_padre] == tipo_corrente:
                profondita += 1
                corrente = id_padre
            else:
                break
            if profondita > 20: break

        if profondita > 0 or ha_figli_stesso_tipo:
            return f"REV.{profondita}"
        return ""

    # Applichiamo la funzione
    df['REVISIONATO'] = df.apply(calcola_revisione, axis=1)

    

    # --- 3. LOGICA RICORSIVA PER TROVARE IL CAPOSTIPITE DI FILIERA ---
    def trova_capostipite(id_doc):
        corrente = id_doc
        passaggi = 0
        while passaggi < 10:
            # 1. Recupera il padre
            padre_logico = mappa_padri.get(corrente, None)
            
            # 2. SE IL PADRE NON ESISTE, HAI TROVATO IL CAPOSTIPITE
            if pd.isna(padre_logico):
                break
                
            # 3. CONTROLLO DI SICUREZZA:
            # Se il padre non esiste nemmeno nel DataFrame, è un aggancio rotto!
            if padre_logico not in mappa_padri:
                break
            
            # 4. SALTA AL PADRE
            corrente = padre_logico
            passaggi += 1
            
        return corrente

    df['ID_FAMIGLIA'] = df['ID_DOCUMENTI'].apply(trova_capostipite)


    # --- LOGICA DI CLASSIFICAZIONE FAMIGLIA ---
    # Creiamo un set dei capostipiti che hanno un 'ORDINE APERTO' nella loro filiera
    famiglie_con_aperto = df[df['TIPO_DOCUMENTO'] == 'ORDINE APERTO']['ID_FAMIGLIA'].unique()

    def assegna_categoria_famiglia(id_fam):
        if id_fam in famiglie_con_aperto:
            return 'APERTO'
        return 'STANDARD'

    # Applichiamo la classificazione
    df['FAMIGLIA'] = df['ID_FAMIGLIA'].apply(assegna_categoria_famiglia)

    # --- 4. CALCOLO DELLO STATUS CON DISTINZIONE DELLE DECURTAZIONI ---
    famiglie_con_ordine = df[df['TIPO_DOCUMENTO'] == 'ORDINE']['ID_FAMIGLIA'].unique()
    famiglie_con_aperto = df[df['TIPO_DOCUMENTO'] == 'ORDINE APERTO']['ID_FAMIGLIA'].unique()

    def determina_status(row):
        tipo = row['TIPO_DOCUMENTO']
        id_doc = row['ID_DOCUMENTI']
        id_fam = row['ID_FAMIGLIA']
        padre = row['ID_DOCUMENTO_PADRE']
        titolo = str(row['TITOLO']).upper()
        categoria_famiglia = row['FAMIGLIA']
        is_acquisto_diretto = 'FORMAZIONE' in titolo or 'CORSO' in titolo
        is_chpr = 'CHPR' in titolo
        
        # 1. PRIORITÀ MASSIMA: Decurtazioni
        if is_chpr:
            if pd.notna(padre):
                if tipo == 'ORDINE APERTO': return f"DECURTAZIONE ORDINE APERTO ID: {int(padre)}"
                return f"DECURTAZIONE ORDINE ID: {int(padre)}"
            return "DECURTAZIONE ORFANA"
        
        # 2. PRIORITÀ ALTA: Ordini Speciali
        if tipo == 'ORDINE':
            
            # Se non ha padre, è un ordine "nudo"
            is_padre_mancante = pd.isna(padre) or (isinstance(padre, (int, float)) and padre == 0)
            if is_padre_mancante:
                if is_acquisto_diretto: 
                    return 'ACQUISTO DIRETTO'
                return 'ATTENZIONE'
            
            # Se ha padre ma non esiste nel file, è orfano
            elif padre not in df['ID_DOCUMENTI'].values:
                return 'ORFANO'
            
            # Se ha padre ed è in una famiglia APERTA, è aggiudicato (priorità sull'attesa)
            elif categoria_famiglia == 'APERTO':
                return 'VOCE AGGIUDICATA'
            
            # Se arriviamo qui, è un ordine standard collegato
            return 'ORDINE STANDARD'

        # 3. PRIORITÀ MEDIA: Preventivi (solo se NON è già stato marcato come altro)
        if tipo == 'PREVENTIVO':
            famiglia_tutta = df[df['ID_FAMIGLIA'] == id_fam]
            # Cerchiamo ordini reali nella famiglia
            ha_ordini = famiglia_tutta[famiglia_tutta['TIPO_DOCUMENTO'].isin(['ORDINE', 'ORDINE APERTO'])].any().any()
            
            if not ha_ordini:
                return 'IN ATTESA'
            return '' # O altro stato se necessario

        return ""


    df['status'] = df.apply(determina_status, axis=1)

    # --- 4.1 CALCOLO DELLE DECURTAZIONI DA SOTTRARRE ---
    df_chpr_collegate = df[df['status'].astype(str).str.contains('DECURTAZIONE ORDINE ID:|DECURTAZIONE ORDINE APERTO ID:')]
    mappa_sconti_chpr = {}
    for idx, row_chpr in df_chpr_collegate.iterrows():
        id_padre_reale = int(row_chpr['ID_DOCUMENTO_PADRE'])
        valore_storno = float(row_chpr['TOTALE_RIGA'])
        mappa_sconti_chpr[id_padre_reale] = mappa_sconti_chpr.get(id_padre_reale, 0.0) + valore_storno



    # --- 5. ORDINAMENTO SEQUENZIALE LOGICO (Priorità: Ragione Sociale) ---
    
    # Assicuriamoci che la ragione sociale sia pulita e pronta per l'ordinamento
    df['RAGIONE_SOCIALE'] = df['RAGIONE_SOCIALE'].astype(str).str.strip().str.upper()

    # Creazione Path Gerarchico
    df['ID_DOCUMENTI'] = pd.to_numeric(df['ID_DOCUMENTI'], errors='coerce').fillna(0).astype(int)
    df['ID_DOCUMENTO_PADRE'] = pd.to_numeric(df['ID_DOCUMENTO_PADRE'], errors='coerce').fillna(0).astype(int)
    
    # Ordiniamo prima per Ragione Sociale, poi per padre, poi per ID
    df = df.sort_values(by=['RAGIONE_SOCIALE', 'ID_DOCUMENTO_PADRE', 'ID_DOCUMENTI'])
    
    path_map = {}
    def get_path(row):
        id_doc = int(row['ID_DOCUMENTI'])
        padre = int(row['ID_DOCUMENTO_PADRE'])
        # Se è un capostipite, il path inizia col cliente (per raggruppare i blocchi)
        if padre == 0 or padre not in df['ID_DOCUMENTI'].values:
            path = f"{row['RAGIONE_SOCIALE']}_{id_doc:010d}"
        else:
            path_padre = path_map.get(padre, f"{row['RAGIONE_SOCIALE']}_{padre:010d}")
            path = f"{path_padre}.{id_doc:010d}"
        path_map[id_doc] = path
        return path

    df['SORT_PATH'] = df.apply(get_path, axis=1)
    
    # Ordine finale basato sul path "Cliente_Padre.Figlio"
    df = df.sort_values(by=['SORT_PATH'])



    # --- 6. DEFINIZIONE SICURA DI df_pulito ---
    # Eliminiamo le colonne di servizio PRIMA di rinominare
    df_pulito = df.drop(columns=['GERARCHIA_TIPO', 'SORT_PATH'], errors='ignore')
    
    if 'DATA' in df_pulito.columns:
        df_pulito['DATA'] = pd.to_datetime(df_pulito['DATA']).dt.date

    # Rinomina colonne
    df_pulito = df_pulito.rename(columns={
        'ID_DOCUMENTI': 'ID_DOC',
        'ID_DOCUMENTO_PADRE': 'ID_PADRE',
        'TIPO_DOCUMENTO': 'TIPOLOGIA',
        'REVISIONATO': 'REV',
        'PREZZO': 'COSTO',
        'status': 'STATUS'
    })

    # --- 7. GESTIONE SELETTORI INTERFACCIA STREAMLIT ---
    col1, col2 = st.columns(2)
    with col1:
        semplifica = st.toggle("Vista Semplificata (Nascondi articoli e mostra solo i documenti)", value=True)
        nascondi_inutili = st.toggle("Nascondi colonne superflue", value=True)

    # --- 8. CONFIGURAZIONE DEI BLOCCHI DI COLONNE BASE ---
    colonne_superflue = ['SEZIONALE', 'NUMERO', 'ID_UTENTI', 'ID_AGENTI', 'ID_CLIENTI', 'FAMIGLIA']
    client_cols = [
        'ID_CLIENTI', 'RAGIONE_SOCIALE', 'PIVA', 'ATECO', 'NUM_DIPE', 
        'SITO_WEB', 'TELEFONO', 'EMAIL', 'NAZIONE', 'REGIONE', 'PROVINCIA', 'COMUNE', 'CAP', 'INDIRIZZO'
    ]
    art_cols_restanti = [
        'ID_DOCUMENTI_RIGHE', 'CODICE_IVA', 'SCONTO1', 'SCONTO2', 'SCONTO3', 
        'SCONTO_IMPORTO', 'RIGA_SCONTO_TOTALE', 'RIGA_ARTICOLO_MANUALE', 'RIGA_MANUALE'
    ]
    doc_cols_restanti = ['SEZIONALE', 'NUMERO', 'ID_UTENTI', 'ID_AGENTI']

    styler_format = {}

    # --- 9. CONFIGURAZIONE VISTE E CALCOLO MATEMATICO PULITO DEI TOTALI ---
    df_calc = df_pulito.copy()
    mask_chpr = df_calc['STATUS'].astype(str).str.contains('DECURTAZIONE ORDINE ID:|DECURTAZIONE ORDINE APERTO ID:')
    df_calc['ID_DOC_ORIGINALE'] = df_calc['ID_DOC']
    df_calc.loc[mask_chpr, 'ID_DOC'] = df_calc.loc[mask_chpr, 'ID_PADRE']
    totale_rettificato_per_doc = df_calc.groupby('ID_DOC')['TOTALE_RIGA'].sum().to_dict()

    if semplifica:
        df_visualizzazione = df_pulito.copy().drop_duplicates(subset=['ID_DOC'])
        df_visualizzazione['TOTALE_RIGA'] = df_visualizzazione['ID_DOC'].map(totale_rettificato_per_doc)
        df_visualizzazione = df_visualizzazione[~df_visualizzazione['STATUS'].astype(str).str.contains('DECURTAZIONE ORDINE ID:|DECURTAZIONE ORDINE APERTO ID:')]
        colonne_ordinate = (['ID_DOC', 'ID_PADRE', 'FAMIGLIA', 'TIPOLOGIA', 'STATUS', 'REV', 'DATA', 'TOTALE_RIGA', 'EVASO', 'TITOLO'] + doc_cols_restanti + client_cols + ['ID_FAMIGLIA'])
        df_visualizzazione = df_visualizzazione[colonne_ordinate]
        styler_format['TOTALE_RIGA'] = "€ {:,.2f}"
    else:
        df_visualizzazione = df_pulito.copy()
        df_visualizzazione['TOTALE_RIGA'] = df_visualizzazione.apply(
            lambda r: totale_rettificato_per_doc.get(r['ID_DOC'], r['TOTALE_RIGA']) if 'DECURTAZIONE' not in str(r['STATUS']) else float(r['TOTALE_RIGA']), 
            axis=1
        )
        colonne_ordinate = (['ID_DOC', 'ID_PADRE', 'FAMIGLIA', 'TIPOLOGIA', 'STATUS', 'REV', 'DATA', 'QT', 'COSTO', 'TOTALE_RIGA', 'EVASO', 'TITOLO', 'CODICE', 'DESCRIZIONE', 'ID_ARTICOLI'] + doc_cols_restanti + art_cols_restanti + client_cols + ['ID_FAMIGLIA'])
        df_visualizzazione = df_visualizzazione[colonne_ordinate]
        styler_format['QT'] = "{:d}"
        styler_format['COSTO'] = "€ {:,.2f}"
        styler_format['TOTALE_RIGA'] = "€ {:,.2f}"

    # --- 10. FUNZIONE DI COLORAZIONE ---
    def colora_filiera_avanzato(data):
        styles = pd.DataFrame('', index=data.index, columns=data.columns)
        famiglie_in_ordine = data['ID_FAMIGLIA'].unique()
        mappa_macro_blocco = {id_fam: i for i, id_fam in enumerate(famiglie_in_ordine)}
        colonne_visibili = [c for c in data.columns if c != 'ID_FAMIGLIA']
        for idx, row in data.iterrows():
            id_fam = row['ID_FAMIGLIA']
            tipo_doc = row['TIPOLOGIA']
            status = str(row['STATUS'])
            indice_blocco = mappa_macro_blocco[id_fam]
            
            if status == 'ATTENZIONE':
                bg_color = 'background-color: #fff200; color: #cc0000; font-weight: bold;'
            elif 'DECURTAZIONE ORDINE ID:' in status or 'DECURTAZIONE ORDINE APERTO ID:' in status:
                bg_color = 'background-color: #ffcccc; color: #800000; font-weight: bold;'
            elif 'DECURTAZIONE ORFANA' in status:
                bg_color = 'background-color: #ff3333; color: #ffffff; font-weight: bold;'
            elif status == 'ACQUISTO DIRETTO':
                bg_color = 'background-color: #555555; color: #ffffff; font-weight: bold;'
            elif 'ORFANO' in status or 'STANDALONE' in status:
                bg_color = 'background-color: #e9e9e9; color: #333333;'
            elif indice_blocco % 2 == 0:
                if tipo_doc == 'PREVENTIVO':
                    bg_color = 'background-color: #d1e6ff; color: #002244; font-weight: bold;'
                    if status == 'IN ATTESA':
                        bg_color = 'background-color: #ffff99; color: #856404; font-weight: bold;'
                elif tipo_doc == 'ORDINE APERTO':
                    bg_color = 'background-color: #a3cfff; color: #002244;'
                else:
                    bg_color = 'background-color: #80bfff; color: #002244; font-weight: bold;'
            else:
                if tipo_doc == 'PREVENTIVO':
                    bg_color = 'background-color: #d2f8d2; color: #0b300b; font-weight: bold;'
                    if status == 'IN ATTESA':
                        bg_color = 'background-color: #ffff99; color: #856404; font-weight: bold;'
                elif tipo_doc == 'ORDINE APERTO':
                    bg_color = 'background-color: #a4f0a4; color: #0b300b;'
                else:
                    bg_color = 'background-color: #80e680; color: #0b300b; font-weight: bold;'
            styles.loc[idx, colonne_visibili] = bg_color
        return styles

    # --- 11. FILTRO TAB E APPLICAZIONE (Aggiornato) ---

    # Sostituiamo la logica basata sulla ricerca degli ID con una suddivisione diretta per categoria
    df_ordini = df_visualizzazione[df_visualizzazione['FAMIGLIA'] == 'STANDARD']
    df_ordini_aperti = df_visualizzazione[df_visualizzazione['FAMIGLIA'] == 'APERTO']

    styler_ordini = df_ordini.style.apply(colora_filiera_avanzato, axis=None).format(styler_format, na_rep="")
    styler_aperti = df_ordini_aperti.style.apply(colora_filiera_avanzato, axis=None).format(styler_format, na_rep="")

    # Manteniamo la logica di pulizia colonne già definita
    colonne_da_mostrare = [c for c in colonne_ordinate if c != 'ID_FAMIGLIA']
    if nascondi_inutili:
        colonne_da_mostrare = [c for c in colonne_da_mostrare if c not in colonne_superflue]

    # --- 12. VISUALIZZAZIONE ---
    tab1, tab2, tab3 = st.tabs(["🛒 ORDINI STANDARD", "📂 ORDINI APERTI", "⚠️ CHPR DIAGNOSI"])
    with tab1:
        st.dataframe(styler_ordini, use_container_width=True, hide_index=True, column_order=colonne_da_mostrare)
    with tab2:
        st.dataframe(styler_aperti, use_container_width=True, hide_index=True, column_order=colonne_da_mostrare)
    with tab3:
        # ... (diagnostica invariata) ...
        df_diagnostica = df_pulito[df_pulito['STATUS'].astype(str).str.contains('DECURTAZIONE')].drop_duplicates(subset=['ID_DOC', 'TITOLO']).copy()
        if not df_diagnostica.empty:
            diagnostica_rows = []
            for _, r in df_diagnostica.iterrows():
                titolo_raw = str(r['TITOLO'])
                match_num = re.search(r'\d+', titolo_raw)
                numero_estratto = int(match_num.group()) if match_num else "NON TROVATO"
                esiste_nel_file = "✅ SÌ" if "ID:" in str(r['STATUS']) else "❌ NO"
                diagnostica_rows.append({
                    "ID_DOC": r['ID_DOC'], "ID_PADRE": r['ID_PADRE'], "Tipologia": r['TIPOLOGIA'],
                    "TITOLO": titolo_raw, "STATUS": r['STATUS'], "ORDINE": numero_estratto,
                    "Importo": f"€ {float(r['TOTALE_RIGA']):,.2f}", "Aggancio": esiste_nel_file
                })
            st.dataframe(pd.DataFrame(diagnostica_rows), use_container_width=True, hide_index=True)
        else:
            st.info("💡 Nessuna decurtazione rilevata.")