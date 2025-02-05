from cat.mad_hatter.decorators import tool, hook
from .utils import get_orders, generate_order, confirm_order, auto_order, get_partner_id_by_name, get_product_by_name, delete_order
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
    ]
)
def get_order_status(tool_input, cat):
    """Rispondi a "Qual è lo stato dei miei ordini", e domande simili. Input è sempre None.."""

    mark = get_orders()

    output = cat.llm(
        f""" Scrivi in modo chiaro per l'utente, applicando una formattazione adeguata i dati contenuti in questa tabella
            e inoltre completa la tabella con una descrizione per il prodotto in base al nome.
        {mark}

        Fornisci sempre un riassunto degli ordini. Ad esempio, quanti ordini sono in bozza, quanti sono stati completati, ecc.
        """, stream = True)
    
    output = output.replace("**", "")

    return output

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
    return generate_order(partner_id, parsed_order_lines, name, currency_id, company_id, user_id)


@tool (
    return_direct=True,
    examples=[
        "Conferma l'ordine con ID 1",
        "Approva l'ordine 1",
        "Accetta l'ordine 1",
        "Conferma l'ordine 1",
        "Completa l'ordine 1",
        "Finalizza l'ordine 1",
        "Concludi l'ordine 1"
        ]
)

def conferma_ordine_odoo(tool_input: str, cat) -> str:
    """
    Tool per Cheshire Cat AI: conferma un ordine d'acquisto in Odoo.

    :param tool_input: ID dell'ordine da confermare.
    :param cat: Contesto Cheshire Cat (non usato direttamente in questa funzione).
    :return: Messaggio con l'esito dell'operazione.
    """
    try:
        #TODO aggiungere validazione per l'ID dell'ordine
        order_id = int(tool_input)
    except ValueError:
        return "Errore: l'ID dell'ordine deve essere un intero valido."

    return confirm_order(order_id)

@tool (
    return_direct=True,
    examples=[
        "Cancella l'ordine con ID 1",
        "Elimina l'ordine 1",
        "Annulla l'ordine 1",
        "Rimuovi l'ordine 1",
        ]
)

def cancella_ordine_odoo(tool_input: str, cat) -> str:
    """
    Tool per Cheshire Cat AI: Cancella più ordini d'acquisto in Odoo.

    :param tool_input: Lista di ID degli ordini da cancellare (separati da virgola).
    :param cat: Contesto Cheshire Cat (non usato direttamente in questa funzione).
    :return: Messaggio con l'esito dell'operazione.
    """
    try:
        # Converte la stringa di input in una lista di interi
        order_ids = [int(order_id.strip()) for order_id in tool_input.split(',')]
    except ValueError:
        return "Errore: tutti gli ID degli ordini devono essere interi validi."

    # Cancella gli ordini uno per uno
    for order_id in order_ids:
        delete_order(order_id)

    return f"{len(order_ids)} ordine/i cancellato/i con successo."

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
