import matplotlib.pyplot as plt
import pandas as pd
from cat.mad_hatter.decorators import tool
from .utils import *
import datetime
import re


@tool(
    return_direct=True,
    examples=[
        "Generare un report dettagliato sullo stato del magazzino",
        "Mostrami lo stato attuale del magazzino in un report",
        "Genera un report sullo stato del magazzino",
        "Produci il report sullo stato del magazzino mostrando i punti chiave",
    ]
)
def generate_report(tool_input, cat):

    """ Genera un report dettagliato sullo stato del magazzino """

    # Ottieni i dati dal magazzino
    stock_data_mrk, stock_data = get_stock_report()
    stock_movement_mrk, stock_movement = get_stock_movements()
    supplier_performance_data_mrk, supplier_performance_data = get_supplier_performance_data()

    # Prepara il prompt per il modello LLM
    prompt = f"""
    Genera un report dettagliato e unificato in tempo reale che copra i seguenti aspetti:

    # **Titolo: Report Generale del Magazzino**

    ## **1. Introduzione:**
    - Fornisci una panoramica generale dello stato attuale del magazzino, evidenziando livelli di stock, movimenti recenti e performance dei fornitori.
    - Specifica che l’obiettivo è monitorare i livelli di stock, tracciare entrate/uscite e valutare l’efficienza dei fornitori.
    - Indica la periodicità del report (ad esempio, mensile, settimanale, ecc.).

    ---

    ## **2. Livelli di Stock:**
    Analizza e organizza le informazioni di ogni prodotto nel magazzino con dettagli utili, identifica prodotti con basso stock o a rischio esaurimento.
    - Nome Prodotto
    - Quantità
    - Stato (🟢 OK, 🟠 Attenzione, 🔴 Critico)
    - Prezzo Unitario (€), Prezzo Totale (€)

    Dati disponibili:
    {stock_data_mrk}

    Fai una sintesi delle principali osservazioni emerse dal report.
    Indicazioni su eventuali azioni da intraprendere, come l'adeguamento dei livelli di stock o il riordino di prodotti con scorte basse.
    Commento finale sullo stato dei livelli di stock del magazzino e suggerimenti per miglioramenti.
    Indica che il threshold è stato impostato al 20% della soglia minima, e spiega come sono indicati i tre livelli di stato.

    ---

    ## **3. Movimenti di Magazzino (Entrate/Uscite):**
    Fornire una breve panoramica dello stato attuale del magazzino.
    Descrivere gli obiettivi principali del report, come l'analisi dei movimenti recenti.
    Fare un cenno alla periodicità del report (ad esempio, mensile, settimanale, ecc.).
    - Nome Prodotto
    - Data, Tipo Movimento (🟢 Entrata, 🔴 Uscita)
    - Quantità, Fornitore, Email (se sconosciuto, testo in corsivo grigio chiaro)

    Dati disponibili:
    {stock_movement_mrk}

    Sintesi delle principali osservazioni emerse dal report.
    Indicazioni su eventuali azioni da intraprendere.
    Analisi sui movimenti in entrata e su quelli in uscita.
    Commento finale sullo stato generale del magazzino e suggerimenti per miglioramenti.

    ---

    ## **4. Performance dei Fornitori:**
    Fornire una panoramica generale delle performance dei fornitori per i prodotti in magazzino.
    Descrivere gli obiettivi principali del report, come l'analisi dei tempi di consegna, dei costi e dell'affidabilità.
    Analizza i seguenti indicatori per ogni fornitore:
    - Nome Fornitore, Quantità Totale, Prezzo Totale (€)
    - Tempo di Consegna, Ritardo di Consegna, Performance (🟢 Buono, 🟠 Migliorabile, 🔴 Critico)

    Dati disponibili:
    {supplier_performance_data_mrk}

    Specifica che il Tempo Medio di Consegna e il Ritardo Medio di Consegna sono espressi in numero di giorni.
    Sintesi delle principali osservazioni emerse dal report.
    Identificare i fornitori con il miglior tempo di consegna e la minor percentuale di ritardi
    Evidenziazione dei fornitori più performanti, con suggerimenti per miglioramenti.
    Raccomandazioni per ottimizzare il processo di approvvigionamento.

    ---

    ## **5. Conclusione:**
    Sintetizza le principali osservazioni:
    - Livelli di stock: evidenzia prodotti critici o a rischio esaurimento.
    - Movimenti: commenta su eventuali variazioni anomale nelle entrate/uscite.
    - Fornitori: identifica i migliori fornitori e quelli con performance da migliorare.
    Fornisci suggerimenti per: riordino di prodotti critici, ottimizzazione delle consegne, collaborazione con fornitori più affidabili.
    Concludi con un breve commento generale sullo stato complessivo del magazzino.

    ---

    ## **Formato e Stile:**
    - **Organizzazione:** Ogni sezione deve essere separata in modo evidente e presentata in formato tabellare (DataFrame) con dati numerici e osservazioni.
    - **Codici Colore:** 
    - Verde: "OK", "Entrata" e "Buono"
    - Arancione: "Attenzione" e "Migliorabile"
    - Rosso: "Critico" e "Uscita"
    - **Tipografia:** Usa grassetto e diverse dimensioni di testo per migliorare la leggibilità.
    - **Stile:** Formale ma chiaro e conciso, con una struttura visiva ordinata per facilitare la comprensione immediata delle informazioni.
    """

    # Richiesta al modello LLM
    output = cat.llm(
        prompt,
        stream=True,
    )

    if stock_data_mrk != "" and stock_movement_mrk != "" and supplier_performance_data_mrk != "":
        write_pdf(output, "report_magazzino", stock_data, stock_movement, supplier_performance_data)

    return output



@tool(
    return_direct=True,
    examples=[
        "Generare un report dettagliato sui livelli di stock del magazzino",
        "Mostrami lo stato attuale dei livelli di stock del magazzino in un report",
        "Genera un report sullo stato degli stock nel magazzino",
        "Genera un report che mi mostri il valore totale in euro che abbiamo in magazzino",
        "Mostrami in modo dettagliato per ogni prodotto quanto abbiamo in magazzino",
        "Generare un report dettagliato sull'analisi dei livelli di scorte del magazzino",
        "Mostrami i prodotti con basso stock o a rischio esaurimento",
        "Genera un report sui prodotti a basso stock o a rischio esaurimento",
    ]
)
def generate_stock_report(tool_input, cat):

    """ Genera un report dettagliato sui livelli di stock del magazzino """

    # Ottieni i dati dal magazzino
    stock_data_mrk, stock_data = get_stock_report()

    # Prepara il prompt per il modello LLM
    prompt = f"""
    Genera un report dettagliato in tempo reale sui seguenti aspetti:

    Titolo: Report Livelli di Stock nel Magazzino
    
    1. **Introduzione:**
    Fornire una breve panoramica dello stato attuale dei livelli di stock del magazzino.
    Descrivere gli obiettivi principali del report, come il controllo dei livelli di stock.
    Fare un cenno alla periodicità del report (ad esempio, mensile, settimanale, ecc.).

    2. **Livelli di Stock:** 
    Analizza e organizza le informazioni di ogni prodotto nel magazzino con dettagli utili, identifica prodotti con basso stock o a rischio esaurimento.
    Dati da includere:
    - Nome Prodotto			 
    - Quantità
    - Stato (🟢 OK, 🟠 Attenzione, 🔴 Critico)
    - Prezzo Unitario (€)
    - Prezzo Totale (€)

    3. **Conclusione:**
    Sintesi delle principali osservazioni emerse dal report.
    Indicazioni su eventuali azioni da intraprendere, come l'adeguamento dei livelli di stock o il riordino di prodotti con scorte basse.
    Commento finale sullo stato dei livelli di stock del magazzino e suggerimenti per miglioramenti.
    Indica che il threshold è stato impostato al 20% della soglia minima, e spiega come sono indicati i tre livelli di stato.

    Dati disponibili:
    {stock_data_mrk}
    

    Obiettivo del Report:
    Organizzare il report in paragrafi distinti e ben strutturati, presentato in formato tabellare o DataFrame, per garantire una facile lettura e comprensione.

    Struttura del Report:
    Organizzazione Chiara: Ogni sezione deve essere separata in modo evidente, con paragrafi ben definiti e facili da distinguere.
    Formato Tabellare: Il report deve essere fornito come un DataFrame o in formato tabellare. Ogni sezione dovrebbe contenere dati numerici e osservazioni riguardanti i livelli di stock.
    Tipografia e Chiarezza: Utilizzare il grassetto e/o diverse dimensioni di testo per rendere il report più leggibile e distinguere chiaramente le varie sezioni.
    Stato dei Prodotti: I livelli di stock devono essere facilmente comprensibili. Utilizzare codici di colore per indicare lo stato dei prodotti:
    Verde per "OK" e "Entrata"
    Arancione per "Attenzione"
    Rosso per "Critico" e "Uscita"
    Stile: Il report deve avere uno stile formale, ma chiaro e conciso, con una buona organizzazione visiva e testuale per facilitare la comprensione immediata delle informazioni.


																												
    """

    # Richiesta al modello LLM
    output = cat.llm(
        prompt,
        stream=True,
    )
    
    if stock_data:
        write_pdf(output, "report_livelli_stock", stock_data)

    return output



@tool(
    return_direct=True,
    examples=[
        "Genera un report dettagliato sui movimenti del magazzino, entrate e uscite",
        "Mostrami le entrate e le uscite dal magazzino", 
        "Mostrami i prodotti in movimento in entrata e in uscita dal magazzino",
        "Genera un report con l'analisi dei movimenti recenti del magazzino",
        "Mostra i prodotti ricevuti o spediti recentemente",
        "Mostrami il report di entrate e uscite dal magazzino",
    ]
)
def generate_report_stock_movements(tool_input, cat):

    """ Genera un report dettagliato sui movimenti del magazzino (entrate e uscite) """

    # Ottieni i dati dal magazzino
    stock_movement_mrk, stock_movement = get_stock_movements()

    # Prepara il prompt per il modello LLM
    prompt = f"""
    Genera un report dettagliato in tempo reale sui seguenti aspetti:
    
    Titolo: Report Movimenti del Magazzino

    1. **Introduzione:**

    Fornire una breve panoramica dello stato attuale del magazzino.
    Descrivere gli obiettivi principali del report, come l'analisi dei movimenti recenti.
    Fare un cenno alla periodicità del report (ad esempio, mensile, settimanale, ecc.).
    
    2. **Movimenti di Magazzino (Entrate/Uscite)**
    Mostra i prodotti ricevuti o spediti recentemente.
    Dati da includere:
    - Nome del Prodotto
						 
    - Data
    - Tipo Movimento (🟢 Entrata, 🔴 Uscita)
    - Quantità
    - Fornitore (Se il fornitore è sconosciuto, utilizzare un testo in corsivo grigio chiaro per differenziarlo)
							 
    - Email del Fornitore    

    3. **Conclusione:**
    Sintesi delle principali osservazioni emerse dal report.
    Indicazioni su eventuali azioni da intraprendere.
    Analisi sui movimenti in entrata e su quelli in uscita.
    Commento finale sullo stato generale del magazzino e suggerimenti per miglioramenti.

    Dati disponibili:
    {stock_movement_mrk}
    

    Obiettivo del Report:
    Organizzare il report in paragrafi distinti e ben strutturati, presentato in formato tabellare o DataFrame, per garantire una facile lettura e comprensione.

    Struttura del Report:
    Organizzazione Chiara: Ogni sezione deve essere separata in modo evidente, con paragrafi ben definiti e facili da distinguere.
    Formato Tabellare: Il report deve essere fornito come un DataFrame o in formato tabellare. Ogni sezione dovrebbe contenere dati numerici e osservazioni riguardanti i livelli di stock.
    Tipografia e Chiarezza: Utilizzare il grassetto e/o diverse dimensioni di testo per rendere il report più leggibile e distinguere chiaramente le varie sezioni.
    Stato dei Prodotti: I livelli di stock devono essere facilmente comprensibili. Utilizzare codici di colore per indicare lo stato dei prodotti:
    Verde per "OK" e "Entrata"
    Arancione per "Attenzione"
    Rosso per "Critico" e "Uscita"
    Stile: Il report deve avere uno stile formale, ma chiaro e conciso, con una buona organizzazione visiva e testuale per facilitare la comprensione immediata delle informazioni.

																												
    """

    # Richiesta al modello LLM
    output = cat.llm(
        prompt,
        stream=True,
    )
    if stock_movement_mrk != "":
        write_pdf(output, "report_movimenti_magazzino", stock_movement)

    return output



@tool(
    return_direct=True,
    examples=[
        "Genera un report dettagliato sulle performance dei fornitori",
        "Mostrami l'analisi delle performance dei fornitori per i prodotti in magazzino",
        "Genera un report sulle performance dei fornitori basato sui tempi di consegna e sui prezzi",
        "Mostra le performance dei fornitori, evidenziando i tempi di consegna e i costi",
        "Analizza i fornitori per tempi di consegna e affidabilità",
    ]
)
def generate_supplier_performance_report(tool_input, cat):

    """ Genera un report dettagliato sulle performance dei fornitori, analizzando tempi di consegna, costi e affidabilità """

    # Ottieni i dati sui fornitori e sui prodotti in magazzino
    supplier_performance_data_mrk, supplier_performance_data = get_supplier_performance_data()

    # Prepara il prompt per il modello LLM
    prompt = f"""
    Genera un report dettagliato sulle performance dei fornitori per i prodotti in magazzino, considerando i seguenti aspetti:

    Titolo: Report Performance Fornitori

    1. **Introduzione:**
    Fornire una panoramica generale delle performance dei fornitori per i prodotti in magazzino.
    Descrivere gli obiettivi principali del report, come l'analisi dei tempi di consegna, dei costi e dell'affidabilità.

    2. **Analisi delle Performance dei Fornitori:**
    Analizzare i dati relativi a ciascun fornitore, includendo le seguenti informazioni:
    - Fornitore
																													 
    - Quantità Totale: quantità totale acquistata per ogni fornitore
    - Prezzo Totale: il totale dei prezzi degli ordini effettuati a ciascun fornitore
    - Tempo di Consegna: il tempo medio tra la data prevista di consegna dell'ordine e la data effettiva di ricezione
    - Ritardo di Consegna: il ritardo medio tra la data dell'ordine e la data di consegna per ogni fornitore
    - Performance: indicatore di performance del fornitore (🟢 Buono, 🟠 Migliorabile, 🔴 Critico)

    Specifica che il Tempo di Consegna e il Ritardo di Consegna sono espressi in numero di giorni.

    3. **Conclusione:**
    Sintesi delle principali osservazioni emerse dal report.
    Identificare i fornitori con il miglior tempo di consegna e la minor percentuale di ritardi
    Evidenziazione dei fornitori più performanti, con suggerimenti per miglioramenti.
    Raccomandazioni per ottimizzare il processo di approvvigionamento.

    Dati disponibili:
    {supplier_performance_data_mrk}


    Obiettivo del Report:
    Organizzare il report in paragrafi distinti e ben strutturati, presentato in formato tabellare o DataFrame, per garantire una facile lettura e comprensione.

    Struttura del Report:
    Organizzazione Chiara: Ogni sezione deve essere separata in modo evidente, con paragrafi ben definiti e facili da distinguere.
    Formato Tabellare: Il report deve essere fornito come un DataFrame o in formato tabellare. Ogni sezione dovrebbe contenere dati numerici e osservazioni riguardanti i livelli di stock.
    Tipografia e Chiarezza: Utilizzare il grassetto e/o diverse dimensioni di testo per rendere il report più leggibile e distinguere chiaramente le varie sezioni.
    Stato dei Prodotti: I livelli di stock devono essere facilmente comprensibili. Utilizzare codici di colore per indicare lo stato dei prodotti:
    Verde per "OK", "Entrata" e "Buono"
    Arancione per "Attenzione" e "Migliorabile"
    Rosso per "Critico" e "Uscita"
    Stile: Il report deve avere uno stile formale, ma chiaro e conciso, con una buona organizzazione visiva e testuale per facilitare la comprensione immediata delle informazioni.
																								  

																												
    """

    # Richiesta al modello LLM
    output = cat.llm(
        prompt,
        stream=True,
    )


    if supplier_performance_data_mrk != "":
        write_pdf(output, "report_performance_fornitori", supplier_performance_data)

    return output


