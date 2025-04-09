import pandas as pd
from cat.experimental.form import CatForm, CatFormState, form
from cat.mad_hatter.decorators import hook, tool
from pydantic import BaseModel, constr
from .utili import *


@tool(
    return_direct=True,
    examples=[
        "Quali sono le date di scadenza dei prodotti che ho in magazzino",
        "Dammi le date di scadenza"
    ],
)
def get_the_warehouse_expiration_dates(tool_input, cat):
    """Rispondi a "Quali sono le date di scadenza dei prodotti che ho in magazzino", e domande simili. Input è sempre None.."""

    mark, _ = get_expiration_dates()
    if mark == "null":
        return "Nessun prodotto trovato"
    output = cat.llm(
        f"""Riscrivi, in modo chiaro per l'utente, applicando una formattazione con tabella, i prodotti e le date di scadenza contenuti in questa tabella:
        
        {mark}
        
        Non mostrare la quantità disponibile
        """,
        stream=True,
    )
    output = output.replace("**", "")

    return output


@tool(
    return_direct=True,
    examples=[
        "Quali sono i prodotti che scadono entro ... giorni?",
    ],
)
def get_the_expiring_products(tool_input, cat):
    """Rispondi a "Quali sono i prodotti che scadono entro ... giorni/mesi/anni?", dove i giorni/mesi/anni sono inseriti in Input dall'utente...
    Se l'input è inserito in mesi o anni viene convertito automaticamente in giorni."""

    mark, _ = get_expiring_products(tool_input)

    if mark == "null":
        return "Nessun prodotto trovato"
    output = cat.llm(
        f"""Riscrivi, in modo chiaro per l'utente, i prodotti che stanno per scadere entro la data inserita in input contenuti in questa tabella:
        
        {mark}
        
        Usa questa formattazione:
        "
        1. Nome prodotto: data di scadenza (in formato dd-mm-YYYY)
        2. Nome prodotto: data di scadenza (in formato dd-mm-YYYY)
        "
        Non mostrare quantità disponibile, quantità riservata e quantità minima
        """,
        stream=True,
    )
    output = output.replace("**", "")

    return output


