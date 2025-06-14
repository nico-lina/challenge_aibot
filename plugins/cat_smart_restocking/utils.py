import pandas as pd
import odoorpc
import psycopg2 as psql
from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import datetime, timedelta
from rapidfuzz import process, fuzz
import telepot
import mailtrap as mt

# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# import os


def connect(db):
    """ Connette al database PostgreSQL """
    try:
        params = {
            'host': 'host.docker.internal',
            'database': 'db_final',
            'user': 'admin',
            'password': 'admin',
            'port': '5433'
        }
        return psql.connect(**params)
    except (Exception, psql.DatabaseError) as error:
        print(f"Errore di connessione al database: {error}")
        return None

def get_odoo_connection():
    """ Connette a Odoo """
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)
    odoo.login('health_final', 'admin', 'admin')
    return odoo

def get_product_by_name(product_name):

    odoo = get_odoo_connection()
    Product = odoo.env['product.product']
    
    products = Product.search_read([], ['name'])
    
    if not products:
        return None
    
    # Lista dei nomi dei prodotti nel database
    product_names = [product['name'] for product in products]

    # Ricerca fuzzy per trovare i prodotti simili
    matches = process.extract(product_name, product_names, scorer=fuzz.ratio, limit=10)  # Prendiamo fino a 10 migliori risultati
    print("MATCHES: ", matches)
    # Controlla se esiste un match con score >= 90
    best_match = next((match[0] for match in matches if match[1] >= 80), None)
    
    if best_match:
        # Troviamo il prodotto esatto
        matched_product = next(prod for prod in products if prod['name'] == best_match)
        return {
            "id": matched_product["id"],
            "name": matched_product["name"]
        }
    else: 
        return None
    # Se nessun match supera 90, filtra quelli con score > 50
    valid_matches = [match[0] for match in matches if match[1] > 45]

    if not valid_matches:
        return None
    
    # Troviamo i prodotti corrispondenti nel database
    matched_products = [prod for prod in products if prod['name'] in valid_matches]
    
    return {
        "multiple_matches": [
            {"id": prod["id"], "name": prod["name"]}
            for prod in matched_products
        ]
    }

def predict_future_demand(id, months: int):
    """Predice la domanda futura per prodotto su base mensile basandosi sui dati storici degli ordini."""
    odoo = get_odoo_connection()
    PurchaseLine = odoo.env['purchase.order.line']
    
    product_id = get_product_by_name(id)

    if product_id is None:
        return "null"
    try:
        quantity = PurchaseLine.search_read([('product_id', '=', product_id['id'])], ['date_planned', 'name', 'product_qty'])
    except Exception as e:
        return f"Errore (Dettaglio: {e})"
    df = pd.DataFrame(quantity)
    df["order_date"] = pd.to_datetime(df["date_planned"])
    
    # Aggregazione della quantità totale per prodotto e mese
    df["year_month"] = df["order_date"].dt.to_period("M")
    df = df.groupby(['name', 'year_month'])['product_qty'].sum().reset_index()
    
    # Convertire il periodo in un valore numerico per la regressione
    df["months_since_start"] = (df["year_month"].astype(str).astype("datetime64") - df["year_month"].min().to_timestamp()).dt.days // 30
    df["months_since_start"] = df["months_since_start"].astype(int)  # Ensure it's an integer type
        
    predictions = {}
    
    months = int(months)

    for product in df["name"].unique():
        product_df = df[df["name"] == product]
        
        X = product_df[["months_since_start"]]
        y = product_df["product_qty"]
        
        model = LinearRegression()
        model.fit(X, y)
        
        future_months = np.arange(product_df["months_since_start"].max() + 1, 
                                  product_df["months_since_start"].max() + months + 1).reshape(-1, 1)
        future_predictions = model.predict(future_months)
        
        predictions[product] = {str((df["year_month"].max() + i).to_timestamp().strftime('%Y-%m')): pred 
                                for i, pred in enumerate(future_predictions, 1)}
    
    return predictions


def suggest_reorder_date(name, months_ahead=3):
    """
    Suggerisce la migliore data per il riordino basandosi sulla domanda prevista,
    in modo da non scendere sotto la quantità minima.
    """
    odoo = get_odoo_connection()
    StockWarehouse = odoo.env['stock.warehouse.orderpoint']
    PurchaseLine = odoo.env['purchase.order.line']
    print("name", name)
    id = get_product_by_name(name)
    print("ID",id)
    if id is None:
        return "null"
    try:
        # Recupero dati di stock e ordini
        stock_data = StockWarehouse.search_read([('product_id', '=', id['id'])], ['product_id', 'product_min_qty', 'product_max_qty'])
        order_data = PurchaseLine.search_read([('product_id', '=', id['id'])], ['product_id', 'name', 'product_qty', 'date_planned'])
    except Exception as e:
        return f"Errore (dettaglio: {e})"
    stock_df = pd.DataFrame(stock_data)
    order_df = pd.DataFrame(order_data)

    if stock_df.empty:
        return "null"
    if order_df.empty:
        return "null"

    order_df.rename(columns={'date_planned': 'date_order'}, inplace=True)
    order_df['date_order'] = pd.to_datetime(order_df['date_order'])

    for i in range(len(stock_df)):
        stock_df.at[i, 'product_id'] = stock_df.at[i, 'product_id'][0]

    for i in range(len(order_df)):
        order_df.at[i, 'product_id'] = order_df.at[i, 'product_id'][0]

    # Unire i dati di stock con gli ordini
    stock_df = stock_df.merge(order_df, on='product_id', how='left')
    
    reorder_dates = {}
    
    # Ottieni previsioni della domanda futura per i prossimi mesi
    future_demand = predict_future_demand(name, months_ahead)
    
    for _, row in stock_df.iterrows():
        product_id = row['product_id']
        product_name = row['name']
        current_stock = row['product_qty']
        min_qty = row['product_min_qty']
        
        # Se il prodotto non ha previsioni, salta
        if product_name not in future_demand:
            continue

        # Convertire la previsione mensile in un consumo giornaliero stimato
        future_demand_values = list(future_demand[product_name].values())
        avg_daily_demand = sum(future_demand_values) / (months_ahead * 30)
        
        reorder_date = datetime.today()

        # Simula il consumo futuro per determinare la data di riordino
        while current_stock > min_qty:
            current_stock -= avg_daily_demand
            reorder_date += timedelta(days=1)
        
        reorder_dates[product_name] = reorder_date.strftime('%Y-%m-%d')

    return reorder_dates


def send_telegram_notification(telegram_text):
    TOKEN = "7539382660:AAHvKE6ovESYyNjodPmVknXmnQqj3omXTiM"
    #TOKEN = "8042065744:AAF-t4WC2Gb5t7ckcYMGnmTXJmYPtZNuXzM"
    bot = telepot.Bot(TOKEN)
    bot.sendMessage(7878972936, telegram_text, parse_mode="HTML")

def send_telegram_notification_2(telegram_text):
    TOKEN = "7539382660:AAHvKE6ovESYyNjodPmVknXmnQqj3omXTiM"
    #TOKEN = "8042065744:AAF-t4WC2Gb5t7ckcYMGnmTXJmYPtZNuXzM"
    bot = telepot.Bot(TOKEN)
    bot.sendMessage(145386464, telegram_text, parse_mode="HTML")

# Funzione principale per gestire gli ordini ai fornitori
def process_supplier_orders(prodotto):

    odoo = get_odoo_connection()
    ResPartner = odoo.env['res.partner']
    PurchaseLine = odoo.env['purchase.order.line']

    # Recupero dati di stock e ordini
    order_data = PurchaseLine.search_read([('name', '=', prodotto)], ['partner_id', 'name'])
    supplier_data = ResPartner.search_read([], ['complete_name', 'commercial_partner_id', 'email'])

    order_df = pd.DataFrame(order_data)
    suppliers_df = pd.DataFrame(supplier_data)

    suppliers_df.rename(columns={'commercial_partner_id': 'partner_id'}, inplace=True)
    suppliers_df.rename(columns={'complete_name': 'supplier_name'}, inplace=True)

    print(suppliers_df)

    suppliers_df = suppliers_df.merge(order_df, on='partner_id', how='left')

    for supplier in suppliers_df:
        product = supplier["name"]
        
        reorder_date = suggest_reorder_date(product, 3)
        
        if reorder_date[product] <= datetime.today().strftime('%Y-%m-%d'):
            return supplier["email"]



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
