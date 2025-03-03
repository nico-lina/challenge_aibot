import pandas as pd
import odoorpc
import psycopg2 as psql
import mailslurp_client
from mailslurp_client import ApiClient, SendEmailOptions
import telepot
import mailtrap as mt


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
    odoo = odoorpc.ODOO("host.docker.internal", port=8069)  # Cambia host e porta se necessario

    # Autenticazione
    db = "health_final"
    username = "admin"
    password = "admin"
    odoo.login(db, username, password)

    # Modelli Odoo
    Product = odoo.env["product.product"]
    StockQuant = odoo.env["stock.quant"]
    OrderPoint = odoo.env["stock.warehouse.orderpoint"]

    # Recupero prodotti con quantità disponibili a magazzino
    products = Product.search_read([], ["id", "name"])

    # Dizionario per raccogliere i dati aggregati
    product_data = {}

    for product in products:
        product_id = product["id"]
        product_name = product["name"]

        # Ottieni le quantità per il prodotto
        quants = StockQuant.search_read(
            [("product_id", "=", product_id), ("location_id", "=", 8)],
            ["quantity", "reserved_quantity"],
        )
        orderpoint = OrderPoint.search_read(
            [("product_id", "=", product_id)], ["product_min_qty"]
        )
        min_qty = orderpoint[0]["product_min_qty"] if orderpoint else 0  # Default a 0 se non impostata

        # Inizializza il prodotto nel dizionario se non esiste
        if product_id not in product_data:
            product_data[product_id] = {
                "Prodotto": product_name,
                "Quantità Disponibile": 0,
                "Quantità Riservata": 0,
                "Quantità Minima di Riordino": min_qty,
            }

        # Somma le quantità per lo stesso prodotto
        for quant in quants:
            product_data[product_id]["Quantità Disponibile"] += quant["quantity"]
            product_data[product_id]["Quantità Riservata"] += quant["reserved_quantity"]

    # Creazione DataFrame
    df = pd.DataFrame(product_data.values())

    if df.empty:
        return "Nessun prodotto disponibile in magazzino", df
    
    df = df[df["Quantità Disponibile"] >= 0]

    # Stampa il DataFrame
    mark = df.to_markdown(index=False)

    return mark, df


def create_product(product_name, product_qty, product_min_qty, product_description, product_price):
    odoo = odoorpc.ODOO("host.docker.internal", port=8069)

    # Autenticazione
    db = "health_final"
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
            "type" : 'consu',
            "standard_price" : product_price,
            "list_price" : product_price,
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
    mail = mt.Mail(
    sender=mt.Address(email="hello@demomailtrap.co", name="Mailtrap Test"),
    to=[mt.Address(email="lorenzooglietti1@gmail.com")],
    subject= mail_sbj,
    html=mail_text,
    category="Notifica magazzino",
)

    client = mt.MailtrapClient(token="102559b73322273cc1d082e1a4a16b9b")
    response = client.send(mail)
    print(response)


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
    db = "health_final"
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

     # Autenticazione
    db = "health_final"
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


# key-2tMtprQhzSbmrzAFHk9MzfCrSU6Euw2DPMXoQIFckGxCZqYpvMU8sIwJhOHbAi0EmOODoHjoGS7r5ApRRhMKaRJYdXzdBM86
