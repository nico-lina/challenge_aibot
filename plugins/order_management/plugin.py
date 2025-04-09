from cat.mad_hatter.decorators import tool
from .utils import get_orders, generate_order, auto_order, delete_order, complete_order, get_partner_id_by_name, get_product_by_name, get_order_details
import json
from pydantic import BaseModel, constr, validator, Field, root_validator
import re
import word2number as w2n
from cat.plugins.super_cat_form.super_cat_form import SuperCatForm, form_tool, super_cat_form



@tool(
    return_direct=True,
    examples=[
        "Qual è lo stato degli ordini?",
        "Mostrami gli ordini confermati?",
        "Quali ordini sono in bozza",
        "Mostrami solo gli ordini confermati",
        "Mostrami solo gli ordini completati",
        
    ]
)

def get_order_status(tool_input, cat):
    """Rispondi a domande sullo stato degli ordini e filtra per stato se richiesto."""
    mark = get_orders()
    if mark == "null":
        return "Nessun prodotto trovato"
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
        Fornisci sempre un riassunto degli ordini.
        {mark}
        """, stream=True)
    
    return output.replace("**", "")


class OrderLine(BaseModel):
    product: str = Field(..., description = "Nome del prodotto da ordinare")
    quantity: int = Field(..., gt = 0)

    @validator("product")
    @classmethod
    def validate_product_name(cls, v):
        product_data = get_product_by_name(v)
        if not product_data:
            raise ValueError(f"Errore: Il prodotto '{v}' non esiste. Inserisci un nome valido.")
        if "multiple_matches" in product_data:
            match_list = "\n".join(
                [f"- {prod['name']} (ID: {prod['id']}, Prezzo: {prod['price']}€)" for prod in product_data["multiple_matches"]]
            )
            raise ValueError(f"Errore: '{v}' corrisponde a più prodotti. Scegli uno tra:\n{match_list}")
        return v


class Order(BaseModel):
    supplier_name: str = Field(...)
    order_lines: list[OrderLine] = Field(..., min_items=1, description="Deve contenere almeno un prodotto")
    currency : int = 125

    @validator("supplier_name")
    @classmethod
    def validate_supplier_name(cls, v):
        partner_id = get_partner_id_by_name(v)
        if partner_id is None:
            raise ValueError(f"Errore: Il fornitore '{v}' non esiste. Inserisci un nome valido.")
        return v

@super_cat_form
class OrderForm(SuperCatForm):
    description = "Crea un ordine che include il nome del fornitore (supplier_name), i nomi dei prodotti da ordinare (product) e le quantità (quantity)"
    model_class = Order
    start_examples = ["Voglio fare un ordine", "Voglio ordinare"]
    stop_examples = ["Non voglio più ordinare", "Non voglio fare l'ordine"]
    ask_confirm = True

    def submit(self, form_data):
        supplier_name = form_data['supplier_name']
        order_lines = form_data['order_lines']
        currency = form_data['currency']

        partner_id = get_partner_id_by_name(supplier_name)
        if partner_id is None:
            return {"output": f"Errore: Il fornitore '{supplier_name}' non esiste."}
        
        order_lines_data = []
        for line in order_lines:
            product_data = get_product_by_name(line["product"])
            if not product_data:
                return {"output": f"Errore: Il prodotto '{line['product']}' non esiste."}
            order_lines_data.append((product_data['id'], line["quantity"], product_data['price'], product_data['name']))
        nome_ordine = f"In base alle informazioni dei prodotti forniti: {order_lines_data}, crea un nome per l'ordine in questo modo P001, per farlo univoco usa l'id dell'ordine contenuto nelle informazioni dei prodotti. , IN OUTPUT VOGLIO SOLO UNA STRINGA CON IL NOME DELL'ORDINE"
        result = generate_order(
            partner_id=partner_id,
            order_lines=order_lines_data,
            name= self.cat.llm(nome_ordine),
            currency_id=currency  # Imposta l'ID della valuta corretta se necessario
        )
        prompt = (f"Scrivi che l'ordine è stato creato correttamente e scrivi in maniera riassuntiva i dettagli dell'ordine:\n{result}"
                "Rispondi con una risposta diretta ma comprendendo i dettagli senza aggiungere commenti tuoi")
        return {"output": f"{self.cat.llm(prompt)}"}

    def message_wait_confirm(self):
        prompt = (
            "Riassumiamo brevemente i dettagli raccolti:\n"
            f"{self._generate_base_message()}\n"
            "Dopo il riassunto dei dettaglio Scrivi qualcosa come, 'I dati sono corretti? Posso creare l'ordine nel sistema? Rispondi dicendo Si puoi inserirlo' Nei dettagli non scrivere la valuta"
            "Rispondi con una risposta diretta ma che contenga il riassunto dei dati senza aggiungere commenti tuoi"
        )

        print(self._state)
        return {"output": f"{self.cat.llm(prompt)}"}
    
    def message_incomplete(self):
        prompt = (
            f"Nel form mancano alcuni dettagli:\n{self._generate_base_message()}\n"
            """In base a ciò che è ancora necessario,
            crea un suggerimento per aiutare l'utente a compilare il
            form di creazione dell'ordine."""
            "Rispondi con una risposta diretta ma che includa il riassunto dei dettagli fin'ora inseriti in maniera leggibile per l'utente senza aggiungere commenti tuoi. Nei dettagli non inserire la valuta"
        )
        return {"output": f"{self.cat.llm(prompt)}"}

    def message_closed(self):
        prompt = (
            f"L'utente non vuole più creare l'ordine, scrivigli che stai uscendo dal form di creazione dell'ordine"
            "Rispondi con una risposta diretta senza aggiungere commenti tuoi"
        )

        return {"output": f"{self.cat.llm(prompt)}"}


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
            result.append(f"Errore: ID ordine {order_id} non valido.")
    
    output = cat.llm(
        f"""Scrivi in modo chiaro per l'utente i risultati della chiusura degli ordini. 
        Che sono contenuti in questo elenco. 

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
    
   
    # Filtra le parole, considerando solo quelle che sono numeri
    order_ids = [num for word in words for num in re.findall(r'\d+', word)]

    print("ORDER IDS", order_ids)
    for order_id in order_ids:
        try:
            order_id = int(order_id.strip())
            result.append(delete_order(order_id))
        except ValueError:
            result.append(f"Errore: ID ordine {order_id} non valido.")
    
    output = cat.llm(
        f"""Scrivi in modo chiaro per l'utente i risultati delle cancellazioni degli ordini. 
        Che sono contenuti in questo elenco. 

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
    if mark == "":
        return "Non ho informazioni sui prodotti da riordinare"
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

@tool(
    return_direct=True,
    examples=[ "Dimmi i dettagli dell'ordine 1",
                "Mostrami i dettagli dell'ordine 1",
                "Dammi i dettagli dell'ordine 1"
    ])

def get_order_details_tool(tool_input, cat):
    """Restituisci i dettagli di un ordine specifico."""
    order_id = int(tool_input)
    order_details = get_order_details(order_id)
    
    if not order_details:
        return f"Errore: l'ordine con ID {order_id} non esiste. Inserisci un ID valido."
    
    output = cat.llm(
        f"""Scrivi in modo chiaro per l'utente i dettagli dell'ordine con ID {order_id}. 
        Completa la tabella con una descrizione per il prodotto in base al nome.
        Fornisci sempre un riassunto degli ordini.
        {order_details}
        Se c'è un errore limitati a dire di che errore si tratta, il messaggio deve essere comunque breve

        """, stream=True)
    
    return output.replace("**", "")