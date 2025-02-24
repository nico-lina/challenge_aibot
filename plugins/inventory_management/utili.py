import pandas as pd
import odoorpc
import psycopg2 as psql
import mailslurp_client
from mailslurp_client import ApiClient, SendEmailOptions
import telepot
from datetime import datetime, timedelta

# from config import config


def connect(db):
    """Connect to the PostgreSQL database server"""
    conn = None
    try:
        # read connection parameters

        # params = config(section=db)
        params = {
            "host": "host.docker.internal",
            "database": "health2",
            "user": "odoo",
            "password": "gattaccio",
            "port": "5433",
        }

        # connect to the PostgreSQL server
        # print('Connecting to the PostgreSQL database...')
        conn = psql.connect(**params)

        return conn
    except (Exception, psql.DatabaseError) as error:
        print(error)
    # finally:
    #     if conn is not None:
    #         conn.close()
    #         print('Database connection closed.')


def get_warehouse():
    odoo = odoorpc.ODOO(
        "host.docker.internal", port=8069
    )  # Cambia host e porta se necessario

    # Autenticazione
    db = "health2"
    username = "admin"
    password = "admin"
    odoo.login(db, username, password)

    # Modelli Odoo
    Product = odoo.env["product.product"]
    StockQuant = odoo.env["stock.quant"]
    StockLocation = odoo.env["stock.location"]
    OrderPoint = odoo.env["stock.warehouse.orderpoint"]

    # Recupero prodotti con quantità disponibili a magazzino
    products = Product.search_read([], ["id", "name"])

    # Lista per raccogliere i dati
    data = []

    for product in products:
        product_id = product["id"]
        product_name = product["name"]

        # Ottieni le quantità per il prodotto
        quants = StockQuant.search_read(
            [("product_id", "=", product_id)],
            ["location_id", "quantity", "reserved_quantity"],
        )
        orderpoint = OrderPoint.search_read(
            [("product_id", "=", product_id)], ["product_min_qty"]
        )
        min_qty = (
            orderpoint[0]["product_min_qty"] if orderpoint else 0
        )  # Default a 0 se non è impostata

        for quant in quants:
            location_id = quant["location_id"][0]

            # Ottieni il nome del magazzino dalla location
            location_data = StockLocation.browse(location_id)
            warehouse_name = (
                location_data.display_name if location_data else "Sconosciuto"
            )

            # Aggiungi i dati alla lista
            data.append(
                {
                    "Prodotto": product_name,
                    # 'Magazzino': warehouse_name,
                    "Quantità Disponibile": quant["quantity"],
                    "Quantità Riservata": quant["reserved_quantity"],
                    "Quantità Minima di Riordino": min_qty
                }
            )

    # Creazione DataFrame
    df = pd.DataFrame(data)
    df = df[df["Quantità Disponibile"] >= 0]

    print(df)
    # Stampa il DataFrame
    mark = df.to_markdown(index=False)

    return mark, df


def get_expiration_dates():
    odoo = odoorpc.ODOO(
        "host.docker.internal", port=8069
    )  # Cambia host e porta se necessario

    # Autenticazione
    db = "health2"
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
            [("product_id", "=", product_id)],
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
    print(df)
    mark = df.to_markdown(index=False)

    return mark, df


def get_expiring_products(days_to_expire):

    odoo = odoorpc.ODOO(
        "host.docker.internal", port=8069
        )  # Cambia host e porta se necessario

    # Autenticazione
    db = "health2"
    username = "admin"
    password = "admin"
    odoo.login(db, username, password)

    days_to_expire = int(days_to_expire)

    # Modelli Odoo
    Product = odoo.env["product.product"]
    StockQuant = odoo.env["stock.quant"]

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

        # Ottieni le quantità e le date di scadenza per il prodotto
        quants = StockQuant.search_read(
            [("product_id", "=", product_id)],
            ["quantity", "expiration_date"],
        )

        for quant in quants:
            expiration_date_str = quant.get("expiration_date")
            if expiration_date_str:
                expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d %H:%M:%S")

                # Controlla se la data di scadenza rientra nel limite
                if expiration_date <= expiration_limit:
                    data.append(
                        {
                            "Prodotto": product_name,
                            "Quantità Disponibile": quant["quantity"],
                            "Data di Scadenza": expiration_date_str,
                        }
                    )

    # Creazione DataFrame
    df = pd.DataFrame(data)
    df = df[df["Quantità Disponibile"] > 0]
    df["Data di Scadenza"] = pd.to_datetime(df["Data di Scadenza"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    df = df.sort_values(by="Data di Scadenza", ascending=True)
    df = df.dropna(subset=["Data di Scadenza"])

    # Stampa il DataFrame
    mark = df.to_markdown(index=False)

    return mark, df



def create_product(product_name, product_qty, product_min_qty, product_description):
    odoo = odoorpc.ODOO("host.docker.internal", port=8069)

    db = "health2"
    username = "admin"
    password = "admin"
    odoo.login(db, username, password)

    Product = odoo.env["product.product"]
    StockQuant = odoo.env["stock.quant"]
    StockLocation = odoo.env["stock.location"]
    OrderPoint = odoo.env["stock.warehouse.orderpoint"]

    new_product_id = Product.create(
        {
            "name": product_name,
            "is_storable": True,
            "categ_id": 1,
            "description": product_description,
        }
    )

    location_id = StockLocation.search([("usage", "=", "internal")], limit=1)[0]

    StockQuant.create(
        {
            "product_id": new_product_id,
            "location_id": location_id,
            "quantity": product_qty,
        }
    )

    OrderPoint.create(
        {
            "product_id": new_product_id,
            "location_id": location_id,
            "product_min_qty": product_min_qty,
            "product_max_qty": product_min_qty,
        }
    )

    odoo_url = (
        "http://localhost:8069/web#id={}&model=product.product&view_type=form".format(
            new_product_id
        )
    )
    return [True, odoo_url]


def send_mail(mail_text, mail_sbj):
    # Configura l'API
    configuration = mailslurp_client.Configuration()
    configuration.api_key["x-api-key"] = (
        "5dc12d2c8d8db594054b652023c644844d324a8a3d3694c3a34f7a45283c2dec"
    )

    with ApiClient(configuration) as api_client:
        api_instance = mailslurp_client.InboxControllerApi(api_client)

        # Crea una email temporanea
        inbox = api_instance.create_inbox()
        print(f"Indirizzo email temporaneo: {inbox.email_address}")

        # Invia email dall'inbox creato
        send_options = SendEmailOptions(
            to=["marino.luca07@gmail.com"],
            subject=mail_sbj,
            body=mail_text,
            is_html=True,
        )

        api_instance.send_email(inbox.id, send_options)


def send_telegram_notification(telegram_text):
    TOKEN = "7865121599:AAGWZOQ2Cnmpyr7En0PZC5npYLhSpIQgG5Q"
    bot = telepot.Bot(TOKEN)
    bot.sendMessage(119405630, telegram_text, parse_mode="HTML")


def create_supplier(
    supplier_name,
    supplier_street,
    supplier_city,
    supplier_zip,
    supplier_phone,
    supplier_email,
):
    odoo = odoorpc.ODOO("host.docker.internal", port=8069)

    db = "health2"
    username = "admin"
    password = "admin"
    odoo.login(db, username, password)

    Partner = odoo.env["res.partner"]

    supplier_id = Partner.create(
        {
            "name": supplier_name,
            "street": supplier_street,
            "city": supplier_city,
            "zip": supplier_zip,
            "country_id": 109,
            "phone": supplier_phone,
            "email": supplier_email,
            "supplier_rank": 1,
            "company_type": "company",
        }
    )

    odoo_url = (
        f"http://localhost:8069/web#id={supplier_id}&model=res.partner&view_type=form"
    )
    return [True, odoo_url]


def create_customer(
    customer_name,
    customer_street,
    customer_city,
    customer_zip,
    customer_phone,
    customer_email,
    customer_type,
):
    odoo = odoorpc.ODOO("host.docker.internal", port=8069)

    db = "health2"
    username = "admin"
    password = "admin"
    odoo.login(db, username, password)

    Partner = odoo.env["res.partner"]

    customer_id = Partner.create(
        {
            "name": customer_name,
            "street": customer_street,
            "city": customer_city,
            "zip": customer_zip,
            "country_id": 109,
            "phone": customer_phone,
            "email": customer_email,
            "customer_rank": 1,
            "company_type": customer_type,
        }
    )

    odoo_url = (
        f"http://localhost:8069/web#id={customer_id}&model=res.partner&view_type=form"
    )
    return [True, odoo_url]