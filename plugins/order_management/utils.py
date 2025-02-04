import pandas as pd
import odoorpc
import psycopg2 as psql
from datetime import datetime

# from config import config

def connect(db):
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # read connection parameters
       
        # params = config(section=db)
        params = {'host': 'host.docker.internal', 'database': 'db_test', 'user': 'odoo', 'password': 'password', 'port': '5433'}

        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psql.connect(**params)

        return conn
    except (Exception, psql.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')


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



def generate_order(partner_id, order_lines, name, currency_id=125, company_id=1, user_id=2):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario

    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    # Modelli Odoo
    PurchaseOrder = odoo.env['purchase.order']
    PurchaseOrderLine = odoo.env['purchase.order.line']
    
    # Ottieni la data attuale in formato stringa compatibile con Odoo
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Creazione dell'ordine di acquisto in purchase_order
    order_id = PurchaseOrder.create({
        'partner_id': partner_id,
        'currency_id': currency_id,
        'company_id': company_id,
        'user_id': user_id,
        'state': 'draft',  # L'ordine è inizialmente in bozza
        'date_order': current_datetime,  # Data corretta
        'amount_total': sum(qty * price for _, qty, price in order_lines),
        'name': name,
    })
    
    # Creazione delle linee d'ordine in purchase_order_line
    for product_id, product_qty, price_unit in order_lines:
        PurchaseOrderLine.create({
            'order_id': order_id,
            'product_id': product_id,
            'product_qty': product_qty,
            'price_unit': price_unit,
            'price_subtotal': product_qty * price_unit,
            'price_total': product_qty * price_unit,  # Considerando nessuno sconto o tasse
            'date_planned': current_datetime,  # Data corretta
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