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
        "Genera un report sullo stato del magazzino"
    ]
)
def generate_report(tool_input, cat):

    """ Genera un report dettagliato sullo stato del magazzino """

    # Ottieni i dati dal magazzino
    warehouse_overview, stock_data, low_stock_alert, stock_movement = generate_warehouse_report()

    print('-------- STOCK DATA --------')
    print(stock_data)

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
    Analizza e organizza le informazioni di ogni prodotto nel magazzino con dettagli utili.
    Dati da includere:
    - Nome Prodotto
    - Categoria
    - Quantità Disponibile
    - Ubicazione (Magazzino, Deposito, etc.)
    - Valore Unitario (€)
    - Valore Totale in Magazzino (€)

    4. **Analisi Livello Scorte:** 
    Identifica prodotti con basso stock o a rischio esaurimento.
    Dati da includere:
    - Nome Prodotto
    - Quantità Disponibile
    - Stato Stock (🟢 OK, 🟠 Attenzione, 🔴 Critico)
    
    5. **Movimenti di Magazzino (Entrate/Uscite)**
    Mostra i prodotti ricevuti o spediti recentemente.
    Dati da includere:
    - Nome Prodotto
    - Data Movimento
    - Tipo Movimento (Entrata/Uscita)
    - Quantità
    - Fornitore o Cliente

    6. **Conclusione:**
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

    return output



@tool(
    return_direct=True,
    examples=[
        "Generare un report dettagliato sui livelli di stock del magazzino",
        "Mostrami lo stato attuale dei livelli di stock del magazzino in un report",
        "Genera un report sullo stato degli stock nel magazzino"
    ]
)
def generate_stock_report(tool_input, cat):

    """ Genera un report dettagliato sui livelli di stock del magazzino """

    # Ottieni i dati dal magazzino
    stock_data = get_stock_report()
    low_stock_alert = get_low_stock_alerts()

    # Prepara il prompt per il modello LLM
    prompt = f"""
    Genera un report dettagliato in tempo reale sui seguenti aspetti:
    
    1. **Introduzione:**
    Fornire una breve panoramica dello stato attuale dei livelli di stock del magazzino.
    Descrivere gli obiettivi principali del report, come il controllo dei livelli di stock.
    Fare un cenno alla periodicità del report (ad esempio, mensile, settimanale, ecc.).

    2. **Livelli di Stock:** 
    Analizza e organizza le informazioni di ogni prodotto nel magazzino con dettagli utili.
    Dati da includere:
    - Nome Prodotto
    - Categoria
    - Quantità Disponibile
    - Ubicazione (Magazzino, Deposito, etc.)
    - Valore Unitario (€)
    - Valore Totale in Magazzino (€)

    3. **Analisi Livello Scorte:** 
    Identifica prodotti con basso stock o a rischio esaurimento.
    Dati da includere:
    - Nome Prodotto
    - Quantità Disponibile
    - Stato Stock (🟢 OK, 🟠 Attenzione, 🔴 Critico)

    4. **Conclusione:**
    Sintesi delle principali osservazioni emerse dal report.
    Indicazioni su eventuali azioni da intraprendere, come l'adeguamento dei livelli di stock o il riordino di prodotti con scorte basse.
    Commento finale sullo stato dei livelli di stock del magazzino e suggerimenti per miglioramenti.

    Dati disponibili:
    - **Livelli di Stock:**
    {stock_data}
    - **Analisi Livello Scorte:**
    {low_stock_alert}
    
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

    return output


@tool(
    return_direct=True,
    examples=[
        "Generare un report dettagliato sull'analisi dei livelli di scorte del magazzino",
        "Mostrami i prodotti con basso stock o a rischio esaurimento",
        "Genera un report sui prodotti a basso stock o a rischio esaurimento",
    ]
)
def generate_report_low_stock_alert(tool_input, cat):

    """ Genera un report dettagliato sull'analisi dei livelli di scorte."""

    # Ottieni i dati dal magazzino
    low_stock_alert = get_low_stock_alerts()

    # Prepara il prompt per il modello LLM
    prompt = f"""
    Genera un report dettagliato in tempo reale sui seguenti aspetti:
    
    1. **Introduzione:**
    Fornire una breve panoramica dello stato attuale del magazzino.
    Descrivere gli obiettivi principali del report.
    Fare un cenno alla periodicità del report (ad esempio, mensile, settimanale, ecc.).

    2. **Analisi Livello Scorte:** 
    Identifica prodotti con basso stock o a rischio esaurimento.
    Dati da includere:
    - Nome Prodotto
    - Quantità Disponibile
    - Stato Stock (🟢 OK, 🟠 Attenzione, 🔴 Critico)

    3. **Conclusione:**
    Sintesi delle principali osservazioni emerse dal report.
    Indicazioni su eventuali azioni da intraprendere, come l'adeguamento dei livelli di stock o il riordino di prodotti con scorte basse.
    Commento finale sullo stato generale del magazzino e suggerimenti per miglioramenti.

    Dati disponibili:
    - **Analisi Livello Scorte:**
    {low_stock_alert}
    
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

    return output


@tool(
    return_direct=True,
    examples=[
        "Genera un report dettagliato sui movimenti del magazzino (entrate e uscite)".
        "Mostrami le entrate e le uscite dal magazzino", 
        "Mostrami i prodotti in movimento (entrata e uscita) dal magazzino",
        "Genera un report con l'analisi dei movimenti recenti del magazzino",
        "Mostra i prodotti ricevuti o spediti recentemente"
    ]
)
def generate_report_stock_movements(tool_input, cat):

    """ Genera un report dettagliato sui movimenti del magazzino (entrate e uscite) """

    # Ottieni i dati dal magazzino
    stock_movement = get_stock_movements()

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
    - Nome Prodotto
    - Data Movimento
    - Tipo Movimento (Entrata/Uscita)
    - Quantità
    - Fornitore o Cliente

    3. **Conclusione:**
    Sintesi delle principali osservazioni emerse dal report.
    Indicazioni su eventuali azioni da intraprendere.
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




    # # recuperiamo i dati del magazzino come markdown e poi convertiamo in dataframe
    # warehouse_markdown = get_warehouse()

    # df = get_df_from_markdwon(warehouse_markdown)

    # # cast nel formato corretto
    # df["Quantità Disponibile"] = df["Quantità Disponibile"].astype(float)

    # # Creazione del grafico
    # fig, ax = plt.subplots(figsize=(10, 5))
    # df.plot(kind='bar', x='Prodotto', y='Quantità Disponibile', ax=ax, color='skyblue')

    # ax.set_title("Livelli di Stock nel Magazzino")
    # ax.set_xlabel("Prodotto")
    # ax.set_ylabel("Quantità Disponibile")
    # ax.set_xticklabels(df["Prodotto"], rotation=45, ha="right")

    # # Salviamo il grafico in un file temporaneo
    # # da integrare con l'app che creeremo per la visualizzazione
    # # nome file = stock_chart_{timestamp}
    # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # img_path = f"/tmp/stock_chart_{timestamp}.png"
    # plt.savefig(img_path)
    # plt.close(fig)

    # return {"image": img_path}
