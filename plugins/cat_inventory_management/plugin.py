import pandas as pd
from cat.experimental.form import CatForm, CatFormState, form
from cat.mad_hatter.decorators import hook, tool
from pydantic import BaseModel, constr

from .utili import (
    create_customer,
    create_product,
    create_supplier,
    get_warehouse,
    send_mail,
    send_telegram_notification,
)


@tool(
    return_direct=True,
    examples=[
        "Qual è lo stato del mio magazzino",
        "Come è la situazione del mio magazzino",
        "Dammi qualche informazione sul mio magazzino",
    ],
)
def get_the_warehouse_status(tool_input, cat):
    """Rispondi a "Qual è lo stato del mio magazzino", e domande simili. Input è sempre None.."""

    mark, _ = get_warehouse()

    output = cat.llm(
        f"""Riscrivi, in modo chiaro per l'utente, applicando una formattazione adeguata e senza usare tabelle, i dati contenuti in questa tabella:
        
        {mark}
        
        Non mostrare quantità riservata e quantità minima
        """,
        stream=True,
    )
    output = output.replace("**", "")

    return output


@tool(
    return_direct=True,
    examples=[
        "Aggiungi il prodotto con quantità disponibile iniziale e quantità minima di riordino"
    ],
)
def create_new_product(tool_input, cat):
    """Crea un nuovo prodotto nel magazzino con la quantità specificata e la soglia di riordino.

    Questo tool prende in input il nome del prodotto, la quantità disponibile iniziale e la quantità minima per il riordino.
    Gli input devono essere forniti nel seguente formato:
    - Il primo valore è una stringa contenente il nome del prodotto.
    - Il secondo valore è un numero intero o decimale che rappresenta la quantità iniziale disponibile.
    - Il terzo valore è un numero intero o decimale che indica la quantità minima per il riordino.

    """

    product_name, product_qty, product_min_qty = tool_input.split(",")

    product_name = product_name.replace(" ", "")
    product_qty = float(product_qty.replace(" ", ""))
    product_min_qty = product_min_qty.replace(" ", "")
    product_description = (
        cat.llm(
            f"Genera una descrizione per il prodotto farmaceutico che si chiama {product_name} formattata in HTML"
        )
        .replace("```html", "")
        .replace("```", "")
    )

    result, link = create_product(
        product_name, product_qty, product_min_qty, product_description
    )
    if result:
        output = f'Ho creato il prodotto <a href="{link}" target="_blank"> {product_name}</a>'
        return output
    else:
        return "Non ho potuto creare il prodotto"


@tool(return_direct=True, examples=["Invia una mail al responsabile di magazzino"])
def send_mail_to_wh_manager(tool_input, cat):
    """Invia una mail per notificare i prodotti che stanno per finire al responsabile di magazzino"""
    _, df = get_warehouse()
    df["Quantità Da Riordinare"] = (
        df["Quantità Disponibile"]
        - df["Quantità Riservata"]
        - df["Quantità Minima di Riordino"]
    )
    df_qty_da_ordinare = df[df["Quantità Da Riordinare"] < 0]
    df_qty_da_ordinare["Quantità Da Riordinare"] = (
        df_qty_da_ordinare["Quantità Da Riordinare"] * -1
    )
    df_qty_da_ordinare = df_qty_da_ordinare[["Prodotto", "Quantità Da Riordinare"]]

    df_qty_da_ordinare_mark = df_qty_da_ordinare.to_markdown(index=False)

    mail_text = (
        cat.llm(f"""Prepara il testo di una mail che dica al responsabile di ordinare
                        i seguenti prodotti della tabella {df_qty_da_ordinare_mark}. 
                        Formatta con HTML la mail ma scrivendo solo il body della mail.
                        Inserisci come nome del responsabile Luca Marino. Firmati come il tuo AIbot di Fiducia""")
        .replace("```html", "")
        .replace("```", "")
    )

    send_mail(mail_text, "Notifica Riordino Prodotti")
    telegram_text = (
        cat.llm(f"""Prepara il testo di un messaggio telegram che dica al responsabile di ordinare
                        i seguenti prodotti della tabella {df_qty_da_ordinare_mark}. Formatta la tabella con il tag <code>.
                        Inserisci come nome del responsabile Luca Marino. Firmati come il tuo AIbot di Fiducia""")
        .replace("```html", "")
        .replace("```", "")
    )
    send_telegram_notification(telegram_text)
    return "Mail inviata"


class Supplier(BaseModel):
    supplier_name: constr(min_length=1)
    supplier_street: str
    supplier_city: str
    supplier_zip: constr(min_length=4, max_length=10)
    supplier_phone: constr(min_length=5, max_length=20)
    supplier_email: str


@form
class SupplierForm(CatForm):
    description = "Inserimento di un fornitore"
    model_class = Supplier
    start_examples = [
        "Voglio inserire un nuovo fornitore",
        "Voglio inserire un fornitore",
        "Aiutami ad inserire un fornitore",
        "Aiutami ad inserire un nuovo fornitore",
        "Aggiungiamo un nuovo fornitore",
        "Aggiungiamo un fornitore",
    ]
    stop_examples = [
        "Non voglio più inserire il fornitore",
        "Non voglio più inserire il nuovo fornitore",
        "Ho finito con l'aggiunta di un nuovo fornitore",
        "Ho finito con l'inserimento di un nuovo fornitore",
        "Sì",
        "Sì puoi inserirlo",
    ]

    ask_confirm = True

    def submit(self, form_data):
        result, link = create_supplier(
            supplier_name=form_data["supplier_name"],
            supplier_street=form_data["supplier_street"],
            supplier_city=form_data["supplier_city"],
            supplier_zip=form_data["supplier_zip"],
            supplier_phone=form_data["supplier_phone"],
            supplier_email=form_data["supplier_email"],
        )

        supplier_name = form_data["supplier_name"]

        if result:
            return {
                "output": f'Ho creato il fornitore <a href="{link}" target="_blank"> {supplier_name}</a> -{self._state}'
            }
        else:
            return {"output": "Non ho potuto creare il fornitore"}

    def message_wait_confirm(self):
        prompt = (
            "Riassumiamo brevemente i dettagli raccolti:\n"
            f"{self._generate_base_message()}\n"
            "Dopo il riassunto dei dettaglio Scrivi qualcosa come, 'I dati sono corretti? Posso inserire il fornitore nel sistema? Rispondi dicendo Si puoi inserirlo'"
        )

        print(self._state)
        return {"output": f"{self.cat.llm(prompt)}"}

    def message_incomplete(self):
        prompt = (
            f"Nel form mancano alcuni dettagli:\n{self._generate_base_message()}\n"
            """In base a ciò che è ancora necessario,
            crea un suggerimento per aiutare l'utente a compilare il
            form di inserimento del fornitore"""
        )
        return {"output": f"{self.cat.llm(prompt)}"}


class Customer(BaseModel):
    customer_name: constr(min_length=1)
    customer_street: str
    customer_city: str
    customer_zip: constr(min_length=4, max_length=10)
    customer_phone: constr(min_length=5, max_length=20)
    customer_email: str
    customer_type: str


@form
class CustomerForm(CatForm):
    description = "Inserimento di un cliente"
    model_class = Customer
    start_examples = [
        "Voglio inserire un nuovo cliente",
        "Voglio inserire un cliente",
        "Aiutami ad inserire un cliente",
        "Aiutami ad inserire un nuovo cliente",
        "Aggiungiamo un nuovo cliente",
        "Aggiungiamo un cliente",
    ]
    stop_examples = [
        "Non voglio più inserire il cliente",
        "Non voglio più inserire il nuovo cliente",
        "Ho finito con l'aggiunta di un nuovo cliente",
        "Ho finito con l'inserimento di un nuovo cliente",
        "Sì",
        "Sì puoi inserirlo",
    ]

    ask_confirm = True

    def submit(self, form_data):
        customer_type = self.cat.llm(f"""Prendi questo valore: '{form_data["customer_type"]}'
e capisci se si tratta di una persona fisica o di un'azienda.
Se si tratta di una persona fisica restituisci person altrimenti company.

Rispondi solo person o company
""")
        result, link = create_customer(
            customer_name=form_data["customer_name"],
            customer_street=form_data["customer_street"],
            customer_city=form_data["customer_city"],
            customer_zip=form_data["customer_zip"],
            customer_phone=form_data["customer_phone"],
            customer_email=form_data["customer_email"],
            customer_type=customer_type,
        )

        customer_name = form_data["customer_name"]
        if result:
            return {
                "output": f'Ho creato il cliente <a href="{link}" target="_blank"> {customer_name}</a>'
            }
        else:
            return {"output": "Non ho potuto creare il cliente"}

    def message_wait_confirm(self):
        prompt = (
            "Riassumiamo brevemente i dettagli raccolti:\n"
            f"{self._generate_base_message()}\n"
            "Dopo il riassunto dei dettaglio Scrivi qualcosa come, 'I dati sono corretti? Posso inserire il cliente nel sistema? Rispondi dicendo Si puoi inserirlo'"
        )

        print(self._state)
        return {"output": f"{self.cat.llm(prompt)}"}

    def message_incomplete(self):
        prompt = (
            f"Nel form mancano alcuni dettagli:\n{self._generate_base_message()}\n"
            """In base a ciò che è ancora necessario,
            crea un suggerimento per aiutare l'utente a compilare il 
            form di inserimento del cliente. Digli che il tipo di cliente può essere solo o persona fisica o azienda"""
        )
        return {"output": f"{self.cat.llm(prompt)}"}
