import pandas as pd
import numpy as np
from cat.mad_hatter.decorators import tool
from .utils import predict_future_demand, suggest_reorder_date


@tool(
    return_direct=True,
    examples=[
        "Quanto venderò del prodotto x nei prossimi 6 mesi?",
        "Rispetto alla vendita dei mesi precedenti, quanto venderò per ogni prodotto nei prossimi 6 mesi?"
    ]
)
def predict_quantity(tool_input, cat):
    """
    Rispondi a "Quante unità venderò di un prodotto" e domande simili
    Questo tool prende in input il nome del prodotto e il numero di mesi per cui fare la previsione.
    Gli input devono essere forniti nel seguente formato:
    - Il primo valore è una stringa contenente il nome del prodotto.
    - Il secondo valore è un numero intero che rappresenta il numero di mesi.
    Dall'input devi estrarre solo il nome del prodotto e il numero di mesi, senza caratteri speciali.
    """

    prodotto_input, mesi_input = tool_input.split(", ")

    mark = predict_future_demand(prodotto_input, int(mesi_input))

    output = cat.llm(
        f""" Scrivi in modo chiaro per l'utente, adeguando la formattazione alle previsioni per prodotto che farai
        
        {mark}

        Metti in evidenza le quantità previste mese per mese
        """, stream=True
    )

    return output


@tool(
    return_direct=True,
    examples=[
        "Entro quando devo ordinare il prodotto 1 per non andare sotto la soglia minima?",
        "Quanti prodotti mancano per raggiungere la soglia minima? Devo riordinare?",
        "Quando esaurirò il prodotto 1? Dimmi data di riordino stimata"
    ]
)
def predict_date(tool_input, cat):
    """Rispondi a "Quando dovrò riordinare i prodotti prima di rimanere senza" e domande simili"""

    prodotto_input = cat.llm(
        f""" Da {tool_input} estrai il nome del prodotto per cui fare la previsione.
        L'OUTPUT DEVE ESSERE UNA STRINGA.
        """,
        stream=True
    )

    mark = suggest_reorder_date(prodotto_input)
    output = cat.llm(
        f""" Scrivi in modo chiaro per l'utente, adeguando la formattazione alle previsioni per data e per nome prodotto che farai
        
        {mark}

        Metti in evidenza le date previste per ogni prodotto
        """, stream=True
    )

    return output
