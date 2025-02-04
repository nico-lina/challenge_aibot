from cat.mad_hatter.decorators import tool, hook
from .utils import get_orders, generate_order, confirm_order
import json

@tool(
    return_direct=True,
    examples=[
        "Qual è lo stato dei miei ordini",
        "Come è la situazione dei miei ordini",
        "Dammi qualche informazione sui miei ordini"
    ]
)
def get_order_status(tool_input, cat):
    """Rispondi a "Qual è lo stato dei miei ordini", e domande simili. Input è sempre None.."""

    mark = get_orders()

    output = cat.llm(
        f""" Scrivi in modo chiaro per l'utente, applicando una formattazione adeguata i dati contenuti in questa tabella

        {mark}

        Metti in evidenza gli ordini che non sono ancora stati approvati o completati
        """, stream = True)
    
    output = output.replace("**", "")

    return output

@tool (
    return_direct=True,
    examples=[
        "Crea un ordine d'acquisto per 5 unità di prodotto 1 a 10€ e 10 unità di prodotto 2 a 20€",
        "Vorrei ordinare 5 unità di prodotto 1 a 10€ e 10 unità di prodotto 2 a 20€",
        "Ordina 5 unità di prodotto 1 a 10€ e 10 unità di prodotto 2 a 20€"
        ]
)

def crea_ordine_odoo(tool_input: str, cat) -> str:
    """
    Tool per Cheshire Cat AI: crea un ordine d'acquisto in Odoo con le linee in purchase_order_line.

    :param tool_input: Stringa JSON contenente i parametri:
        - partner_id (int): ID del fornitore.
        - order_lines (list): Lista di dizionari con 'product_id', 'product_qty' e 'price_unit'.
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
    partner_id = data.get("partner_id")
    order_lines = data.get("order_lines")
    name = data.get("name")
    currency_id = data.get("currency_id", 1)
    company_id = data.get("company_id", 1)
    user_id = data.get("user_id", 1)

    # Validazione input
    if not isinstance(partner_id, int):
        #TODO aggiungere validazione per partner_id
        return "Errore: 'partner_id' deve essere un intero valido."
    
    if not isinstance(order_lines, list) or not all(isinstance(item, dict) for item in order_lines):
        return "Errore: 'order_lines' deve essere una lista di dizionari contenenti 'product_id', 'product_qty' e 'price_unit'."
    
    if not isinstance(name, str):
        #TODO aggiungere validazione per il nome
        return "Errore: 'name' deve essere una stringa valida."

    # Parsing delle order_lines
    parsed_order_lines = [(item['product_id'], item['product_qty'], item['price_unit']) for item in order_lines]

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