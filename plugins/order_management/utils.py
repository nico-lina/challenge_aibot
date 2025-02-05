import pandas as pd
import odoorpc
import psycopg2 as psql
from datetime import datetime
from rapidfuzz import process, fuzz
# from config import config

# def connect(db):
#     """ Connect to the PostgreSQL database server """
#     conn = None
#     try:
#         # read connection parameters
       
#         # params = config(section=db)
#         params = {'host': 'host.docker.internal', 'database': 'db_test', 'user': 'odoo', 'password': 'password', 'port': '5433'}

#         # connect to the PostgreSQL server
#         print('Connecting to the PostgreSQL database...')
#         conn = psql.connect(**params)

#         return conn
#     except (Exception, psql.DatabaseError) as error:
#         print(error)
#     finally:
#         if conn is not None:
#             conn.close()
#             print('Database connection closed.')


def get_orders():
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario

    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    # Modelli Odoo
    PurchaseOrder = odoo.env['purchase.order']

    # Recupero ordini con ID, nome e stato
    orders = PurchaseOrder.search_read([], ['id', 'name', 'state'])

    # Creazione DataFrame
    df = pd.DataFrame(orders)

    # Mappa gli stati di Odoo a descrizioni più leggibili
    state_mapping = {
        'draft': 'Bozza',
        'sent': 'Inviato',
        'to approve': 'Da approvare',
        'purchase': 'Ordine confermato',
        'done': 'Completato',
        'cancel': 'Annullato'
    }
    
    df['state'] = df['state'].map(state_mapping).fillna('Sconosciuto')

    # Stampa il DataFrame in formato markdown
    mark = df.to_markdown(index=False)
    
    return mark


def get_partner_id_by_name(partner_name):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)
    
    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    Partner = odoo.env['res.partner']
    partners = Partner.search_read([('name', '=', partner_name)], ['id'])

    return partners[0]['id'] if partners else None


def get_product_by_name(product_name):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)
    
    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    Product = odoo.env['product.product']
    
    products = Product.search_read([], ['id', 'list_price', 'name'])

    if not products:
        return None
    
    # Lista dei nomi dei prodotti nel database
    product_names = [product['name'] for product in products]

    # Ricerca fuzzy per trovare i prodotti simili
    matches = process.extract(product_name, product_names, scorer=fuzz.ratio, limit=10)  # Prendiamo fino a 5 migliori risultati
    
    # Controlla se esiste un match con score >= 90
    best_match = next((match[0] for match in matches if match[1] >= 90), None)

    if best_match:
        # Troviamo il prodotto esatto
        matched_product = next(prod for prod in products if prod['name'] == best_match)
        return {
            "id": matched_product["id"],
            "price": matched_product["list_price"]
        }
    
    # Se nessun match supera 90, filtra quelli con score > 50
    valid_matches = [match[0] for match in matches if match[1] > 50]

    if not valid_matches:
        return None
    
    # Troviamo i prodotti corrispondenti nel database
    matched_products = [prod for prod in products if prod['name'] in valid_matches]

    return {
        "multiple_matches": [
            {"id": prod["id"], "name": prod["name"], "price": prod["list_price"]}
            for prod in matched_products
        ]
    }


def generate_order(partner_id, order_lines, name, currency_id=125, company_id=1, user_id=2):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  

    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    # Modelli Odoo
    PurchaseOrder = odoo.env['purchase.order']
    PurchaseOrderLine = odoo.env['purchase.order.line']
    
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    order_id = PurchaseOrder.create({
        'partner_id': partner_id,
        'currency_id': currency_id,
        'company_id': company_id,
        'user_id': user_id,
        'state': 'draft',
        'date_order': current_datetime,
        'amount_total': sum(qty * price for _, qty, price in order_lines),
        'name': name,
    })
    
    for product_id, product_qty, price_unit in order_lines:
        PurchaseOrderLine.create({
            'order_id': order_id,
            'product_id': product_id,
            'product_qty': product_qty,
            'price_unit': price_unit,
            'price_subtotal': product_qty * price_unit,
            'price_total': product_qty * price_unit,
            'date_planned': current_datetime,
        })
    
    return f"Ordine creato con ID: {order_id}"



def confirm_order(order_id):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario

    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    # Ottieni il record del PurchaseOrder
    purchase_order = odoo.env['purchase.order'].browse(order_id)  # Sostituisci con l'ID del tuo PurchaseOrder

    # Modifica lo stato e la data di approvazione
    purchase_order.write({
    'state': 'purchase',  # Imposta lo stato su 'purchase'
    'date_approve': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Imposta la data di approvazione
})
    return f"Ordine con ID {order_id} confermato con successo."

def auto_order():
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario

    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'        
    password = 'password'
    odoo.login(db, username, password)

   # Modelli Odoo
    Product = odoo.env['product.product']
    StockQuant = odoo.env['stock.quant']
    OrderPoint = odoo.env['stock.warehouse.orderpoint']
    
    # Recupera tutte le regole di riordino
    orderpoints = OrderPoint.search_read([], ['product_id', 'product_min_qty', 'product_max_qty'])
    
    products_below_reorder = []
    
    for orderpoint in orderpoints:
        product_id = orderpoint['product_id'][0]
        min_qty = orderpoint['product_min_qty']
        max_qty = orderpoint['product_max_qty']
        
        # Recupera la quantità attuale a magazzino per il prodotto
        quants = StockQuant.search_read([('product_id', '=', product_id)], ['quantity'])
        current_qty = sum(q['quantity'] for q in quants)
        
        if current_qty < min_qty:
            product_data = Product.browse(product_id)
            products_below_reorder.append({
                'product_id': product_id,
                'name': product_data.name,
                'current_qty': current_qty,
                'min_qty': min_qty,
                'max_qty': max_qty
            })

    df = pd.DataFrame(products_below_reorder)

    mark = df.to_markdown(index=False)
    
    return mark

def delete_order(order_id):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario

    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

     # Ottieni il record del PurchaseOrder
    purchase_order = odoo.env['purchase.order'].browse(order_id)  # Sostituisci con l'ID del tuo PurchaseOrder

    # Modifica lo stato e la data di approvazione
    purchase_order.write({
    'state': 'cancel',  # Imposta lo stato su 'purchase'
    })
    return f"Ordine con ID {order_id} cancellato con successo."


