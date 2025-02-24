import pandas as pd
import odoorpc
import psycopg2 as psql
import mailslurp_client
from mailslurp_client import ApiClient, SendEmailOptions
import telepot

# from config import config


def connect(db):
    """Connect to the PostgreSQL database server"""
    conn = None
    try:
        # read connection parameters

        # params = config(section=db)
        params = {
            "host": "host.docker.internal",
            "database": "health1",
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
    db = "db_test"
    username = "prova@prova"
    password = "password"
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
                    "Quantità Minima di Riordino": min_qty,
                }
            )

    # Creazione DataFrame
    df = pd.DataFrame(data)
    df = df[df["Quantità Disponibile"] >= 0]

    # Stampa il DataFrame
    mark = df.to_markdown(index=False)

    return mark, df


def create_product(product_name, product_qty, product_min_qty, product_description):
    odoo = odoorpc.ODOO("host.docker.internal", port=8069)

    # Autenticazione
    db = "db_test"
    username = "prova@prova"
    password = "password"
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
            "location_id": 8,
            "quantity": product_qty,
        }
    )

    OrderPoint.create(
        {
            "product_id": new_product_id,
            "location_id": 8,
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
    # configuration.api_key["x-api-key"] = (
    #     "5dc12d2c8d8db594054b652023c644844d324a8a3d3694c3a34f7a45283c2dec"
    # )
    configuration.api_key["x-api-key"] = ("8606b4407c80286fcdeb82a056591d091da161ac99133a6c55afcf50561bc53f")
    with ApiClient(configuration) as api_client:
        api_instance = mailslurp_client.InboxControllerApi(api_client)

        # Crea una email temporanea
        inbox = api_instance.create_inbox()
        print(f"Indirizzo email temporaneo: {inbox.email_address}")

        # Invia email dall'inbox creato
        send_options = SendEmailOptions(
            to=["lorenzo.oglietti@libero.it"],
            subject=mail_sbj,
            body=mail_text,
            is_html=True,
        )

        api_instance.send_email(inbox.id, send_options)


def send_telegram_notification(telegram_text):
    TOKEN = "7539382660:AAHvKE6ovESYyNjodPmVknXmnQqj3omXTiM"
    #TOKEN = "7865121599:AAGWZOQ2Cnmpyr7En0PZC5npYLhSpIQgG5Q"
    bot = telepot.Bot(TOKEN)
    bot.sendMessage(145386464, telegram_text, parse_mode="HTML")


def create_supplier(
    supplier_name,
    supplier_street,
    supplier_city,
    supplier_zip,
    supplier_phone,
    supplier_email,
):
    odoo = odoorpc.ODOO("host.docker.internal", port=8069)

    # Autenticazione
    db = "db_test"
    username = "prova@prova"
    password = "password"
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

    # Autenticazione
    db = "db_test"
    username = "prova@prova"
    password = "password"
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


# key-2tMtprQhzSbmrzAFHk9MzfCrSU6Euw2DPMXoQIFckGxCZqYpvMU8sIwJhOHbAi0EmOODoHjoGS7r5ApRRhMKaRJYdXzdBM86
