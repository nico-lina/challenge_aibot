import matplotlib.pyplot as plt
import pandas as pd
from cat.mad_hatter.decorators import tool
from .utils import *
import datetime
import re


# mettere la maggior parte del codice in utils e non in plugin (usare tante funzioni da richiamare)
# tools richiamati dal bot

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
    warehouse_overview, stock_data, stock_movement = generate_warehouse_report()

    # Prepara il prompt per il modello LLM
    prompt = f"""
    Genera un report dettagliato in tempo reale sui seguenti aspetti:
    
    1. **Introduzione:**

    Fornire una breve panoramica dello stato attuale del magazzino.
    Descrivere gli obiettivi principali del report, come il controllo dei livelli di stock, l'analisi dei movimenti recenti e la valutazione del valore complessivo dello stock.
    Fare un cenno alla periodicità del report (ad esempio, mensile, settimanale, ecc.).

    2. **Panoramica Generale del Magazzino:**
    Mostra la situazione attuale con indicatori chiave.
    Dati da includere: 
    - Totale Prodotti in Magazzino (conteggio distinti)
    - Quantità Totale Disponibile
    - Valore Totale dello Stock (€) (sommando il valore di costo di ogni prodotto)
    - Top 5 Prodotti per Disponibilità
    - Top 5 Prodotti per Valore (€)
    
    3. **Livelli di Stock:** 
    Analizza e organizza le informazioni di ogni prodotto nel magazzino con dettagli utili, identifica prodotti con basso stock o a rischio esaurimento.
    Dati da includere:
    - Nome Prodotto
    - Categoria
    - Quantità Disponibile
    - Soglia Minima
    - Threshold
    - Stato (🟢 OK, 🟠 Attenzione, 🔴 Critico)
    - Valore Unitario (€)
    - Valore Totale (€)
    Indica che il threshold è stato impostato al 20% della soglia minima, e spiega come sono indicati i tre livelli di stato.
    
    4. **Movimenti di Magazzino (Entrate/Uscite)**
    Mostra i prodotti ricevuti o spediti recentemente.
    Dati da includere:
    - Nome Prodotto
    - Data Movimento
    - Tipo Movimento (Entrata/Uscita)
    - Quantità
    - Fornitore o Cliente

    5. **Conclusione:**
    Sintesi delle principali osservazioni emerse dal report.
    Indicazioni su eventuali azioni da intraprendere, come l'adeguamento dei livelli di stock o il riordino di prodotti con scorte basse.
    Commento finale sullo stato generale del magazzino e suggerimenti per miglioramenti.

    Dati disponibili:
    - **Panoramica Generale del Magazzino**
    {warehouse_overview}
    - **Livelli di Stock:**
    {stock_data}
    - **Analisi Livello Scorte:**
    {low_stock_alert}
    - **Movimenti di Magazzino**
    {stock_movement}
    
    Organizza il report in paragrafi chiari e ben strutturati, e deve essere fornito in formato tabellare.
    
    Dividi bene i paragrafi per renderli chiari e distinguibili.

    Formato del Report: Il report deve essere fornito come un DataFrame o una tabella, con una chiara separazione tra le sezioni e le informazioni ben organizzate. Ogni sezione dovrà essere facilmente leggibile e comprendere sia i dati numerici che eventuali stati o osservazioni sui livelli di stock.
    Stile: Il report deve essere formale, ma chiaro e conciso. Gli stati dei prodotti devono essere facilmente comprensibili (ad esempio, usare colori per rappresentare lo stato del prodotto: verde per "OK", giallo per "Attenzione", rosso per "Critico").

    """

    # Richiesta al modello LLM
    output = cat.llm(
        prompt,
        stream=True,
    )

    # Rimuovi eventuali formattazioni indesiderate
    output = output.replace("**", "")

    # write_pdf(output, "report_magazzino")

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
    stock_data, _ = get_stock_report()

    # Prepara il prompt per il modello LLM
    prompt = f"""
    Genera un report dettagliato in tempo reale sui seguenti aspetti:
    
    1. **Introduzione:**
    Fornire una breve panoramica dello stato attuale dei livelli di stock del magazzino.
    Descrivere gli obiettivi principali del report, come il controllo dei livelli di stock.
    Fare un cenno alla periodicità del report (ad esempio, mensile, settimanale, ecc.).

    2. **Livelli di Stock:** 
    Analizza e organizza le informazioni di ogni prodotto nel magazzino con dettagli utili, identifica prodotti con basso stock o a rischio esaurimento.
    Dati da includere:
    - Nome Prodotto
    - Categoria
    - Quantità Disponibile
    - Soglia Minima
    - Threshold
    - Stato (🟢 OK, 🟠 Attenzione, 🔴 Critico)
    - Valore Unitario (€)
    - Valore Totale (€)

    3. **Conclusione:**
    Sintesi delle principali osservazioni emerse dal report.
    Indicazioni su eventuali azioni da intraprendere, come l'adeguamento dei livelli di stock o il riordino di prodotti con scorte basse.
    Commento finale sullo stato dei livelli di stock del magazzino e suggerimenti per miglioramenti.
    Indica che il threshold è stato impostato al 20% della soglia minima, e spiega come sono indicati i tre livelli di stato.

    Dati disponibili:
    - **Livelli di Stock:**
    {stock_data}
    
    Organizza il report in paragrafi chiari e ben strutturati, e deve essere fornito in formato tabellare.
    
    Dividi bene i paragrafi per renderli chiari e distinguibili.

    Formato del Report: Il report deve essere fornito come un DataFrame o una tabella, con una chiara separazione tra le sezioni e le informazioni ben organizzate. Ogni sezione dovrà essere facilmente leggibile e comprendere sia i dati numerici che eventuali stati o osservazioni sui livelli di stock.
    Stile: Il report deve essere formale, ma chiaro e conciso. Gli stati dei prodotti devono essere facilmente comprensibili (ad esempio, usare colori per rappresentare lo stato del prodotto: verde per "OK", giallo per "Attenzione", rosso per "Critico").

    """

    # Richiesta al modello LLM
    output = cat.llm(
        prompt,
        stream=True,
    )

    # Rimuovi eventuali formattazioni indesiderate
    output = output.replace("**", "")
    
    # write_pdf(output, "stock_report")

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
    stock_movement, _ = get_stock_movements()

    # Prepara il prompt per il modello LLM
    prompt = f"""
    Genera un report dettagliato in tempo reale sui seguenti aspetti:
    
    1. **Introduzione:**

    Fornire una breve panoramica dello stato attuale del magazzino.
    Descrivere gli obiettivi principali del report, come l'analisi dei movimenti recenti.
    Fare un cenno alla periodicità del report (ad esempio, mensile, settimanale, ecc.).
    
    2. **Movimenti di Magazzino (Entrate/Uscite)**
    Mostra i prodotti ricevuti o spediti recentemente.
    Dati da includere:
    - ID del Prodotto
    - Nome del Prodotto
    - Categoria del Prodotto
    - Data Movimento (usa un formato leggibile)
    - Tipo Movimento (🟢 Entrata, 🔴 Uscita)
    - Quantità (Se la quantità è elevata (es. >100), evidenziarla con un badge per attirare l'attenzione)
    - Fornitore (Se il fornitore è sconosciuto, utilizzare un testo in corsivo grigio chiaro per differenziarlo)
    - Indirizzo del Fornitore
    - Email del Fornitore
    Ordina i dati per Data del Movimento crescente e ID del Prodotto crescente.
    

    3. **Conclusione:**
    Sintesi delle principali osservazioni emerse dal report.
    Indicazioni su eventuali azioni da intraprendere.
    Analisi sui movimenti in entrata e su quelli in uscita.
    Commento finale sullo stato generale del magazzino e suggerimenti per miglioramenti.

    Dati disponibili:
    - **Movimenti di Magazzino**
    {stock_movement}
    
    Organizza il report in paragrafi chiari e ben strutturati, e deve essere fornito in formato tabellare.
    Dividi bene i paragrafi per renderli chiari e distinguibili.

    Formato del Report: Il report deve essere fornito come un DataFrame o una tabella, con una chiara separazione tra le sezioni e le informazioni ben organizzate. Ogni sezione dovrà essere facilmente leggibile e comprendere sia i dati numerici che eventuali stati o osservazioni sui livelli di stock.
    Stile: Il report deve essere formale, ma chiaro e conciso. Gli stati dei prodotti devono essere facilmente comprensibili (ad esempio, usare colori per rappresentare lo stato del prodotto: verde per "OK", giallo per "Attenzione", rosso per "Critico").

    """

    # Richiesta al modello LLM
    output = cat.llm(
        prompt,
        stream=True,
    )

    # Rimuovi eventuali formattazioni indesiderate
    output = output.replace("**", "")

    # write_pdf(output, "report_movimenti_magazzino")

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
    supplier_performance_data, _ = get_supplier_performance_data()

    # Prepara il prompt per il modello LLM
    prompt = f"""
    Genera un report dettagliato sulle performance dei fornitori per i prodotti in magazzino, considerando i seguenti aspetti:

    1. **Introduzione:**
    Fornire una panoramica generale delle performance dei fornitori per i prodotti in magazzino.
    Descrivere gli obiettivi principali del report, come l'analisi dei tempi di consegna, dei costi e dell'affidabilità.

    2. **Analisi delle Performance dei Fornitori:**
    Analizzare i dati relativi a ciascun fornitore, includendo le seguenti informazioni:
    - **Tempo Medio di Consegna**: Calcolare il tempo medio tra la data dell'ordine e la data di approvazione per ogni fornitore.
    - **Affidabilità del Fornitore**: Identificare i fornitori con il miglior tempo di consegna e la minor percentuale di ritardi.
    - **Prezzo Medio per Prodotto**: Calcolare il prezzo medio per ciascun prodotto fornito da ogni fornitore.
    - **Quantità Totale Acquistata**: Sommare la quantità totale acquistata per ogni fornitore.
    - **Totale Ordini**: Sommare il totale degli ordini effettuati a ciascun fornitore.

    Ordina i dati per:
    - Tempo di Consegna medio (dal più breve al più lungo)
    - Prezzo medio per prodotto (dal più basso al più alto)
    - Quantità totale acquistata (dal più alto al più basso)

    3. **Conclusione:**
    Sintesi delle principali osservazioni emerse dal report.
    Evidenziazione dei fornitori più performanti, con suggerimenti per miglioramenti.
    Analisi comparativa dei fornitori per tempi di consegna, costi e affidabilità.
    Raccomandazioni per ottimizzare il processo di approvvigionamento.

    Dati disponibili:
    - **Performance dei Fornitori**
    {supplier_performance_data}

    Organizza il report in paragrafi chiari e ben strutturati, con dati numerici facili da leggere e analizzare.

    Formato del Report: Il report deve essere fornito come un DataFrame o una tabella, con una chiara separazione tra le sezioni e le informazioni ben organizzate. Ogni sezione dovrà essere facilmente leggibile e comprendere sia i dati numerici che eventuali osservazioni sui fornitori.

    Stile: Il report deve essere formale, chiaro e conciso, con una buona separazione delle informazioni per ogni sezione.
    """

    # Richiesta al modello LLM
    output = cat.llm(
        prompt,
        stream=True,
    )

    # Rimuovi eventuali formattazioni indesiderate
    output = output.replace("**", "")

    # write_pdf(output, "report_performance_fornitori")

    return output









@tool(
    return_direct=True,
    examples=[
        "Crea un grafico con i livelli di stock",
        "Qual è la situazione del magazzino? Mostrami un grafico a barre",
    ]
)
def generate_stock_chart(tool_input, cat):

    """ Genera un grafico a barre con i livelli di stock disponibili nel magazzino """

    # Ottieni i dati dal magazzino
    stock_data = get_warehouse_data()

    print(type(stock_data))

    print('-------- PRODOTTI --------')
    prodotti = stock_data['Prodotto']
    print(prodotti)

    print('-------- QUANTITA DISPONIBILI --------')
    quantità_disponibili = stock_data["Quantità Disponibile"]
    print(quantità_disponibili)

    # Creazione del grafico a barre
    plt.figure(figsize=(12, 6))
    plt.bar(prodotti, quantità_disponibili, color='skyblue')
    plt.title('Quantità Disponibile per Prodotto nel Magazzino')
    plt.xlabel('Prodotti')
    plt.ylabel('Quantità Disponibile')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.show()

    filename = "stock_magazzino.png"
    plt.savefig(filename)
    plt.close()
    
    return filename
