import pandas as pd
import numpy as np
from cat.mad_hatter.decorators import tool
from datetime import datetime, timedelta
from .utils import *

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

    if mark == "null":
        return "Nessun prodotto disponibile"

    output = cat.llm(
        f""" Scrivi in modo chiaro per l'utente, adeguando la formattazione alle previsioni per prodotto che farai
        
        {mark}

        Metti in evidenza le quantità previste mese per mese

        Cosa importante, se hai degli errori non inventare le risposte ma riporta l'errore, inoltre non aggiungere commenti tuoi, la risposta deve essere diretta all'utente
        """, stream=True
    )

    return output



@tool(
    return_direct=True,
    examples=[
        "Entro quando devo ordinare il prodotto 1 per non andare sotto la soglia minima?",
        "Quante unità di prodotto X mancano per raggiungere la soglia minima? Devo riordinare?",
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
    mark = suggest_reorder_date(tool_input)
    if mark == "null":
        return f"❌ Qualche dato sul prodotto {tool_input} non è disponibile, non posso fornire la previsione su quando dovrai riordinarlo"
    # Formatta la risposta per l'utente
    output = cat.llm(
        f"""Scrivi in modo chiaro per l'utente, adeguando la formattazione alle previsioni per data e per nome prodotto.
        
        {mark}

        Metti in evidenza le date previste per ogni prodotto.
        Cosa importante, se hai degli errori non inventare le risposte ma riporta l'errore, inoltre non aggiungere commenti tuoi, la risposta deve essere diretta all'utente
        """
    )
    
    mark = pd.to_datetime(list(mark.values())[0])
    if mark - datetime.today() < timedelta(days=20):

        # supplier_email = process_supplier_orders(prodotto_input)

        # Genera il testo della mail per il fornitore
        # mail_text = cat.llm(
        #     f"""Scrivi una mail formale per un fornitore in cui richiedi il riordino del prodotto {prodotto_input}.
        #     Sii conciso e cortese."""
        # )

        # Genera il testo della notifica Telegram
        telegram_text = cat.llm(
            f"""Scrivi un breve messaggio di notifica per informare che la richiesta di riordinare il del prodotto {tool_input} 
            è stato inviato al responsabile di magazzino.
            Firmati come Oodvisor"""
        )

        # Invia la mail
        # send_mail(mail_text, f"Ordine riordino: {prodotto_input}", "camilla.casaleggi@gmail.com")

        # Invia la notifica Telegram
        send_telegram_notification(telegram_text)

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
                            Inserisci come nome del responsabile Lorenzo. Firmati come Oodvisor""")
            .replace("```html", "")
            .replace("```", "")
        )

        send_mail(mail_text, "Notifica Riordino Prodotti")
        telegram_text = (
            cat.llm(f"""Prepara il testo di un messaggio telegram che dica al responsabile di ordinare
                            i seguenti prodotti della tabella {df_qty_da_ordinare_mark}. Formatta la tabella con il tag <code>.
                            Inserisci come nome del responsabile Lorenzo. Firmati come Oodvisor""")
            .replace("```html", "")
            .replace("```", "")
        )
        send_telegram_notification_2(telegram_text)

        return f"""{output}\n
                ✅ Notifica per **{tool_input}** inviata con successo al responsabile di magazzino!"""

    # Se l'utente rifiuta, termina l'operazione
    return output