import pandas as pd
import numpy as np
from cat.mad_hatter.decorators import tool
from datetime import datetime, timedelta
from .utils import predict_future_demand, suggest_reorder_date, process_supplier_orders, send_telegram_notification


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
    """Rispondi a 'Quando dovrò riordinare i prodotti prima di rimanere senza' e domande simili"""

    # Estrai il nome del prodotto
    prodotto_input = cat.llm(
        f"""Da {tool_input} estrai il nome del prodotto per cui fare la previsione.
        L'OUTPUT DEVE ESSERE UNA STRINGA."""
    )

    # Ottieni la data suggerita di riordino
    mark = suggest_reorder_date(prodotto_input)

    # Formatta la risposta per l'utente
    output = cat.llm(
        f"""Scrivi in modo chiaro per l'utente, adeguando la formattazione alle previsioni per data e per nome prodotto.
        
        {mark}

        Metti in evidenza le date previste per ogni prodotto."""
    )
    
    mark = pd.to_datetime(mark)
    if mark - datetime.today() < timedelta(days=20):
    # Se il parametro confirm_order non è stato ancora fornito, chiediamo conferma all'utente
#     if confirm_order is None:
#         return f"""{output}

# ❓ Vuoi procedere con l'ordine per **{prodotto_input}**? Rispondi 'sì' o 'no'."""

#     # Se l'utente conferma l'ordine, lo inviamo
#     if confirm_order.lower() == "sì":
        # supplier_email = process_supplier_orders(prodotto_input)

        # # Genera il testo della mail per il fornitore
        # mail_text = cat.llm(
        #     f"""Scrivi una mail formale per un fornitore in cui richiedi il riordino del prodotto {prodotto_input}.
        #     Sii conciso e cortese."""
        # )

        # Genera il testo della notifica Telegram
        telegram_text = cat.llm(
            f"""Scrivi un breve messaggio di notifica per informare che l'ordine del prodotto {prodotto_input} 
            è stato inviato al fornitore via email."""
        )

        # Invia la mail
        # send_mail(mail_text, f"Ordine riordino: {prodotto_input}")

        # Invia la notifica Telegram
        send_telegram_notification(telegram_text)

        return f"{output}\n✅ Ordine per **{prodotto_input}** inviato con successo al fornitore!"

    # Se l'utente rifiuta, termina l'operazione
    return output


# @tool(
#     return_direct=True,
#     examples=[
#         "Entro quando devo ordinare il prodotto 1 per non andare sotto la soglia minima?",
#         "Quanti prodotti mancano per raggiungere la soglia minima? Devo riordinare?",
#         "Quando esaurirò il prodotto 1? Dimmi data di riordino stimata"
#     ]
# )
# def predict_date(tool_input, cat):
#     """Rispondi a 'Quando dovrò riordinare i prodotti prima di rimanere senza' e domande simili"""

#     # Estrai il nome del prodotto
#     prodotto_input = cat.llm(
#         f""" Da {tool_input} estrai il nome del prodotto per cui fare la previsione.
#         L'OUTPUT DEVE ESSERE UNA STRINGA.
#         """,
#         stream=True
#     )

#     # Ottieni la data suggerita di riordino
#     mark = suggest_reorder_date(prodotto_input)

#     # Formatta la risposta per l'utente
#     output = cat.llm(
#         f""" Scrivi in modo chiaro per l'utente, adeguando la formattazione alle previsioni per data e per nome prodotto che farai
        
#         {mark}

#         Metti in evidenza le date previste per ogni prodotto.
#         """, stream=True
#     )

#     print(output)  # Mostra la previsione all'utente

#     # Chiede conferma all'utente per procedere con l'ordine
#     user_input = input(f"Vuoi procedere con l'ordine per {prodotto_input}? (sì/no): ").strip().lower()

#     if user_input == "sì":
#         supplier_email = process_supplier_orders(prodotto_input)
#         if not supplier_email:
#             return output

#         # Genera il testo della mail con cat.llm
#         mail_text = cat.llm(
#             f"""Scrivi una mail formale per un fornitore in cui richiedi il riordino del prodotto {prodotto_input}.
#             Sii conciso e cortese.""",
#             stream=True
#         )

#         # Genera il testo della notifica Telegram con cat.llm
#         telegram_text = cat.llm(
#             f"""Scrivi un breve messaggio di notifica per informare che l'ordine del prodotto {prodotto_input} 
#             è stato inviato al fornitore {supplier_email} via email.""",
#             stream=True
#         )

#         # Invia l'ordine via email
#         # send_mail(mail_text, f"Ordine riordino: {prodotto_input}")

#         # Invia la notifica Telegram
#         send_telegram_notification(telegram_text)

#         print("Ordine inviato con successo!")

#     else:
#         print("Ordine annullato.")

#     return output


# def predict_date(tool_input, cat):
#     """Rispondi a "Quando dovrò riordinare i prodotti prima di rimanere senza" e domande simili"""

#     prodotto_input = cat.llm(
#         f""" Da {tool_input} estrai il nome del prodotto per cui fare la previsione.
#         L'OUTPUT DEVE ESSERE UNA STRINGA.
#         """,
#         stream=True
#     )

#     mark = suggest_reorder_date(prodotto_input)
#     output = cat.llm(
#         f""" Scrivi in modo chiaro per l'utente, adeguando la formattazione alle previsioni per data e per nome prodotto che farai
        
#         {mark}

#         Metti in evidenza le date previste per ogni prodotto
#         """, stream=True
#     )

#     return output
