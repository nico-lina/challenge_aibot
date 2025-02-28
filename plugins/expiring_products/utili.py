import pandas as pd
import odoorpc
import psycopg2 as psql
import mailslurp_client
from mailslurp_client import ApiClient, SendEmailOptions
import telepot
from datetime import datetime, timedelta

# from config import config




def get_expiration_dates():
    odoo = odoorpc.ODOO(
        "host.docker.internal", port=8069
    )  # Cambia host e porta se necessario

     # Autenticazione
    db = "health_final"
    username = "admin"
    password = "admin"
    odoo.login(db, username, password)

    # Modelli Odoo
    Product = odoo.env["product.product"]
    StockQuant = odoo.env["stock.quant"]

    # Recupero prodotti con quantità disponibili a magazzino
    products = Product.search_read([], ["id", "name"])

    # Lista per raccogliere i dati
    data = []

    for product in products:
        product_id = product["id"]
        product_name = product["name"]

        # Ottieni le quantità per il prodotto
        quants = StockQuant.search_read(
            [("product_id", "=", product_id), ("location_id", "=", 8)],
            ["quantity", "expiration_date"],
        )

        for quant in quants:

            # Aggiungi i dati alla lista
            data.append(
                {
                    "Prodotto": product_name,
                    "Quantità Disponibile": quant["quantity"],
                    "Data di Scadenza": quant.get("expiration_date", "Non specificata"),
                }
            )

    # Creazione DataFrame
    df = pd.DataFrame(data)
    if df.empty:
        return "null", "null"
    df = df[df["Quantità Disponibile"] >= 0]
    df["Data di Scadenza"] = pd.to_datetime(df["Data di Scadenza"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    df = df.dropna(subset=["Data di Scadenza"])
    df = df.sort_values(by="Data di Scadenza", ascending=True)

    # Identifica i prodotti con scadenza imminente
    expiration_limit = datetime.today() + timedelta(days=365)

    # Aggiungi una colonna "Scadenza imminente" con un pallino rosso se la scadenza è entro 1 anno
    df["Scadenza Imminente"] = df["Data di Scadenza"].apply(
        lambda x: "🔴" if x <= expiration_limit else ""
    )

    # Stampa il DataFrame
    mark = df.to_markdown(index=False)

    return mark, df


def get_expiring_products(days_to_expire):

    odoo = odoorpc.ODOO(
        "host.docker.internal", port=8069
    )  # Cambia host e porta se necessario

    # Autenticazione
    db = "health_final"
    username = "admin"
    password = "admin"
    odoo.login(db, username, password)
    
    days_to_expire = int(days_to_expire)

    # Modelli Odoo
    Product = odoo.env["product.product"]
    StockQuant = odoo.env["stock.quant"]
    StockLot = odoo.env["stock.lot"]

    # Calcola la data limite per la scadenza
    today = datetime.today()
    expiration_limit = today + timedelta(days=days_to_expire)

    # Recupero prodotti con quantità disponibili a magazzino
    products = Product.search_read([], ["id", "name"])

    # Lista per raccogliere i dati
    data = []

    for product in products:
        product_id = product["id"]
        product_name = product["name"]

        # Ottieni le quantità e i lotti per il prodotto
        quants = StockQuant.search_read(
            [("product_id", "=", product_id), ("location_id", "=", 8)],
            ["quantity", "lot_id", "company_id"],
        )

        for quant in quants:
            lot_id = quant.get("lot_id")
            expiration_date_str = None

            # Se il lotto esiste, recupera la data di scadenza
            if lot_id:
                lot = StockLot.browse(lot_id[0])  # lot_id è una tupla (id, nome)
                expiration_date_str = lot.expiration_date

            if expiration_date_str:
                # Controlla il tipo di expiration_date_str prima di convertirlo
                if isinstance(expiration_date_str, str):
                    expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d %H:%M:%S")
                else:
                    expiration_date = expiration_date_str  # Se è già datetime, lo usa direttamente

                # Controlla se la data di scadenza rientra nel limite
                if expiration_date <= expiration_limit:
                        data.append(
                            {
                                "Prodotto": product_name,
                                "Quantità Disponibile": quant.get("quantity", 0),
                                "Data di Scadenza": expiration_date,
                            }
                        )

    # Se non ci sono dati, restituisci un messaggio vuoto
    if not data:
        return "Nessun prodotto in scadenza", pd.DataFrame()

    # Creazione DataFrame
    df = pd.DataFrame(data)
    if df.empty:
        return "null", "null"
    # Verifica che la colonna "Quantità Disponibile" esista prima di filtrare
    if "Quantità Disponibile" in df.columns:
        df = df[df["Quantità Disponibile"] > 0]

    df["Data di Scadenza"] = pd.to_datetime(df["Data di Scadenza"], errors="coerce")
    df = df.sort_values(by="Data di Scadenza", ascending=True)
    df = df.dropna(subset=["Data di Scadenza"])

    # Stampa il DataFrame
    mark = df.to_markdown(index=False)

    return mark, df