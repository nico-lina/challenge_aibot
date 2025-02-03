from cat.mad_hatter.decorators import tool, hook
from .utili import connect, get_warehouse, create_product
import pandas as pd

@tool(
    return_direct=True,
    examples=[
        "Qual è lo stato del mio magazzino",
        "Come è la situazione del mio magazzino",
        "Dammi qualche informazione sul mio magazzino"
    ]
)
def get_the_warehouse_status(tool_input, cat):
    """Rispondi a "Qual è lo stato del mio magazzino", e domande simili. Input è sempre None.."""

    mark = get_warehouse()
    
    output = cat.llm(
        f"""Riscrivi, in modo chiaro per l'utente, applicando una formattazione adeguata e senza usare tabelle, i dati contenuti in questa tabella:
        
        {mark}
        
        Non mostrare quantità riservata e quantità minima
        """, stream=True
    )
    output = output.replace("**", "")
    

    return output

@tool(
    return_direct=True,
    examples=["Aggiungi il prodotto con quantità disponibile iniziale e quantità minima di riordino"]
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
    product_min_qty = (product_min_qty.replace(" ", ""))
    product_description = cat.llm(
        f"Genera una descrizione per il prodotto farmaceutico che si chiama {product_name} formattata in HTML"
    ).replace("```html", "").replace("```", "")
    
    result, link = create_product(product_name, product_qty, product_min_qty, product_description)
    if result:
        output = f"Ho creato il prodotto <a href=\"{link}\" target=\"_blank\"> {product_name}</a>"
        return output
    else:
        return "Non ho potuto creare il prodotto"
    
    
