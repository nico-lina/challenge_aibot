from cat.mad_hatter.decorators import tool, hook
from .utils import get_orders, generate_order, confirm_order, auto_order, get_partner_id_by_name, get_product_by_name, delete_order, complete_order
import json

@tool(
    return_direct=True,
    examples=[
        "Qual è lo stato dei miei ordini",
        "Come è la situazione dei miei ordini",
        "Dammi qualche informazione sui miei ordini",
        "Mostrami gli ordini confermati",
        "Mostrami solo gli ordini cancellati",
        "Quali ordini sono stati completati",
        "Quali ordini sono ancora in attesa di approvazione",
        "Quali ordini sono in bozza",
        "Fammi vedere solo gli ordini in bozza",
        "Mostrami solo gli ordini confermati",
        "Mostrami solo gli ordini completati",
        "Mostrami solo gli ordini in attesa di approvazione",
        
    ]
)
def get_order_status(tool_input, cat):
    """Rispondi a domande sullo stato degli ordini e filtra per stato se richiesto."""
    mark = get_orders()
    
    # Se tool_input specifica uno stato, filtriamo gli ordini
    if tool_input:
        stato_richiesto = tool_input.lower()

        # Chiediamo all'LLM di mappare il termine all'eventuale stato corretto
        stato_mappato = cat.llm(
            f"""Se l'utente scrive uno stato dell'ordine (ad esempio "annullati"), restituisci il termine corretto tenendo conto di questa lista di possibili stati:
            'bozza': 'Bozza',
            'inviato': 'Inviato',
            'da approvare': 'Da approvare',
            'confermato': 'Ordine confermato',
            'completato': 'Completato',
            'annullato': 'Annullato', 
            in modo che l'utente riceva lo stato giusto, come ad esempio "annullato" per "annullati". 
            L'input che devo mappare è: "{stato_richiesto}".
            Nel caso sia scritto in inglese traducilo in italiano e poi mappalo.
            L'OUTPUT DEVE ESSERE SEMPRE E SOLO UNA SINGOLA PAROLA CHE RAPPRESENTA IL TERMINE CORRETTO."""
        )
        print("STATO MAPPATO    ", stato_mappato)
        # Rimuoviamo eventuali spazi e normalizziamo la risposta
        stato_richiesto = stato_mappato.strip().lower()

        stati_mappa = {
            'bozza': 'Bozza',
            'inviato': 'Inviato',
            'da approvare': 'Da approvare',
            'confermato': 'Ordine confermato',
            'completato': 'Completato',
            'annullato': 'Annullato'
        }

        stato_filtrato = stati_mappa.get(stato_richiesto)
        
        if stato_filtrato:
            lines = mark.split("\n")
            header, *rows = lines
            filtered_rows = [row for row in rows if stato_filtrato in row]
            mark = "\n".join([header] + filtered_rows) if filtered_rows else "Nessun ordine trovato con stato richiesto."
    
    output = cat.llm(
        f"""Scrivi in modo chiaro per l'utente, applicando una formattazione adeguata i dati contenuti in questa tabella.
        Completa la tabella con una descrizione per il prodotto in base al nome.
        Fornisci sempre un riassunto degli ordini.
        {mark}
        """, stream=True)
    
    return output.replace("**", "")

@tool (
    return_direct=True,
    examples=[
        "Crea un ordine d'acquisto per 5 unità di Lampade da ufficio e 10 unità di Scaffali",
        "Vorrei ordinare 5 unità di Lampade da ufficio e 10 unità di Scaffali",
        "Ordina 5 Lampade da ufficio e 10 unità di Scaffali"
        ]
)

def crea_ordine_odoo(tool_input: str, cat) -> str:
    """
    Tool per Cheshire Cat AI: crea un ordine d'acquisto in Odoo con le linee in purchase_order_line.

    :param tool_input: Stringa JSON contenente i parametri:
        - partner_name (str): Nome del fornitore.
        - order_lines (list): Lista di dizionari con 'product_name' e 'product_qty'.
        - name (str): Nome dell'oggetto da ordinare.
        - currency_id (int, opzionale): ID della valuta usata (default: 1).
        - company_id (int, opzionale): ID dell'azienda (default: 1).
        - user_id (int, opzionale): ID dell'utente che crea l'ordine (default: 1).
    
    :param cat: Contesto Cheshire Cat (non usato direttamente in questa funzione).
    :return: Messaggio con l'ID dell'ordine o errore.
    """
    try:
        # Convertiamo la stringa JSON in un dizionario
        data = json.loads(tool_input)
    except json.JSONDecodeError:
        return "Errore: il tool_input non è in un formato JSON valido."

    # Estrazione parametri
    partner_name = data.get("partner_name")
    order_lines = data.get("order_lines")
    name = data.get("name")
    currency_id = data.get("currency_id", 1)
    company_id = data.get("company_id", 1)
    user_id = data.get("user_id", 1)

    # Validazione input
    if not isinstance(partner_name, str) or not partner_name.strip():
        return "Errore: 'partner_name' deve essere una stringa valida."

    # Recupero dell'ID del fornitore da Odoo
    partner_id = get_partner_id_by_name(partner_name)
    if partner_id is None:
        return f"Errore: Il fornitore '{partner_name}' non esiste."
   
    if not isinstance(order_lines, list) or not all(isinstance(item, dict) for item in order_lines):
        return "Errore: 'order_lines' deve essere una lista di dizionari contenenti 'product_name' e 'product_qty'."
    
    if not isinstance(name, str):
        return "Errore: 'name' deve essere una stringa valida."

    # Recupero degli ID dei prodotti e prezzi dal database
    parsed_order_lines = []
    for item in order_lines:
        product_name = item.get("product_name")
        product_qty = item.get("product_qty")

        if not isinstance(product_name, str) or not product_name.strip():
            return "Errore: 'product_name' deve essere una stringa valida."
        if not isinstance(product_qty, (int, float)) or product_qty <= 0:
            return f"Errore: 'product_qty' per '{product_name}' deve essere un numero positivo."

        product_data = get_product_by_name(product_name)
        
        # Se il prodotto non esiste, errore
        if product_data is None:
            return f"Errore: Il prodotto '{product_name}' non esiste."
        
        # Se ci sono più prodotti simili, restituiamo la lista e chiediamo all'utente di specificare
        if "multiple_matches" in product_data:
            match_list = "\n".join(
                [f"- {prod['name']} (ID: {prod['id']}, Prezzo: {prod['price']}€)" for prod in product_data["multiple_matches"]]
            )
            return f"Errore: '{product_name}' corrisponde a più prodotti. Scegli uno tra:\n{match_list}"

        # Se è un solo prodotto, procediamo con l'ordine
        product_id = product_data["id"]
        price_unit = product_data["price"]

        parsed_order_lines.append((product_id, product_qty, price_unit))


    # Creazione ordine
    order_generated = generate_order(partner_id, parsed_order_lines, name, currency_id, company_id, user_id)

    output = cat.llm(
        f"""Scrivi in modo chiaro per l'utente l'esito della creazione dell'ordine. E riporta in maniera riassuntiva i dettagli dell'ordine:
        {order_generated}
        """, stream=True)
    return output


@tool (
    return_direct=True,
    examples=[
        "Conferma l'ordine con ID 1,2,3",
        "Approva l'ordine 1,3,4",
        "Accetta l'ordine 1,2,3",
        "Conferma l'ordine 1,2,4",
        "Completa l'ordine 1,5,6",
        "Finalizza l'ordine 1,3,4",
        "Concludi l'ordine 1, 2,3"
        ]
)

def confirm_orders_tool(tool_input, cat):
    """Gestisce la conferma di uno o più più ordini, restituendo successi ed errori."""
    result = []
    order_ids = tool_input.split(',')

    for order_id in order_ids:
        try:
            order_id = int(order_id.strip())
            result.append(confirm_order(order_id))
        except ValueError:
            result.append(f"Errore: ID ordine {order_id} non valido. Inserisci un numero intero.")
    
    output = cat.llm(
        f"""Scrivi in modo chiaro per l'utente i risultati delle conferme degli ordini. 
        Che sono contenuti in questo elenco. 
        Per esempio se l'errore è: "Non esiste alcun record ‘purchase.order’ con l’ID 45." Scrivi una cosa come "Errore: l'ID dell'ordine 45 non è valido."

        {result}
        """, stream=True)
    
    return output.replace("**", "")

@tool (
    return_direct=True,
    examples=[
        "Completa l'ordine con ID 1,2,3",
        "Finalizza l'ordine 1,3,4",
        "Concludi l'ordine 1,2,3",
        "Chiudi l'ordine 1,2,4",
        "Termina l'ordine 1,5,6"
    ]
)
def complete_orders_tool(tool_input, cat):
    """Gestisce la chiusura di uno o più ordini, restituendo successi ed errori."""
    result = []
    order_ids = tool_input.split(',')

    for order_id in order_ids:
        try:
            order_id = int(order_id.strip())
            result.append(complete_order(order_id))
        except ValueError:
            result.append(f"Errore: ID ordine {order_id} non valido. Inserisci un numero intero.")
    
    output = cat.llm(
        f"""Scrivi in modo chiaro per l'utente i risultati della chiusura degli ordini. 
        Che sono contenuti in questo elenco. 
        Per esempio se l'errore è: "Non esiste alcun record ‘purchase.order’ con l’ID 45." Scrivi una cosa come "Errore: l'ID dell'ordine 45 non è valido."

        {result}
        """, stream=True)
    
    return output.replace("**", "")

@tool (
    return_direct=True,
    examples=[
        "Cancella l'ordine con ID 1",
        "Elimina l'ordine 1",
        "Annulla l'ordine 1",
        "Rimuovi l'ordine 1",
        ]
)

def delete_order_tool(tool_input, cat):
    """Gestisce la cancellazione di un ordine alla volta, restituendo successi ed errori."""
    result = []

    words = tool_input.split()
    # Rimuove eventuali virgole o altri caratteri non numerici
    cleaned_words = [word.strip(",.").isdigit() and word.strip(",.") or None for word in words]
    
    # Filtra le parole, considerando solo quelle che sono numeri
    order_ids = [word for word in cleaned_words if word is not None]
    for order_id in order_ids:
        try:
            order_id = int(order_id.strip())
            result.append(delete_order(order_id))
        except ValueError:
            result.append(f"Errore: ID ordine {order_id} non valido. Inserisci un numero intero.")
    
    output = cat.llm(
        f"""Scrivi in modo chiaro per l'utente i risultati delle cancellazioni degli ordini. 
        Che sono contenuti in questo elenco. 
        Per esempio se l'errore è: "Non esiste alcun record ‘purchase.order’ con l’ID 45." Scrivi una cosa come "Errore: l'ID dell'ordine 45 non è valido."

        {result}
        """, stream=True)
    
    return output.replace("**", "")

@tool(
    return_direct=True,
    examples=[
        "Quali prodotti mi consigli di riordinare?",
        "Quali prodotti dovrei riordinare?",
        "Cosa mi consigli di riordinare?",
        "Cosa dovrei riordinare?",
        "Quali prodotti mi consigli di riacquistare?",
    ]
)

def get_products_to_reorder(tool_input, cat):
    """Rispondi a "Quali prodotti mi consigli di riordinare?", e domande simili. Input è sempre None.."""

    mark = auto_order()

    output = cat.llm(
       f"""
        Scrivi all'utente in modo chiaro quali prodotti dovrebbe riordinare, applicando una formattazione adeguata ai dati

        {mark}

        e inoltre genera delle frasi che possono essere utilizzate per creare questi ordini di acquisto tenendo conto che questi sono degli esempi
        "Crea un ordine d'acquisto per 5 unità di prodotto X e 10 unità di prodotto X",
        "Vorrei ordinare 5 unità di prodotto X e 10 unità di prodotto X",
        "Ordina 5 unità di prodotto X e 10 unità di prodotto X "
        Dove le X sono i prodotti che dovrebbero essere riordinati e le quantità sono quelle suggerite.
        """, stream = True)
    
    output = output.replace("**", "")

    return output
