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
    """Recupera gli ordini da Odoo e restituisce una tabella formattata."""
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)
    
    PurchaseOrder = odoo.env['purchase.order']
    orders = PurchaseOrder.search_read([], ['id', 'name', 'state'])
    
    df = pd.DataFrame(orders)
    
    state_mapping = {
        'draft': 'Bozza',
        'sent': 'Inviato',
        'to approve': 'Da approvare',
        'purchase': 'Ordine confermato',
        'done': 'Completato',
        'cancel': 'Annullato'
    }
    
    df['state'] = df['state'].map(state_mapping).fillna('Sconosciuto')
    return df.to_markdown(index=False)



def get_partner_id_by_name(partner_name):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)
    
    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    Partner = odoo.env['res.partner']
    partners = Partner.search_read([('name', '=', partner_name)], ['id'])
    print("PARTNER:", partners)
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
    matches = process.extract(product_name, product_names, scorer=fuzz.ratio, limit=10)  # Prendiamo fino a 10 migliori risultati
    print("MATCHES: ", matches)
    # Controlla se esiste un match con score >= 90
    best_match = next((match[0] for match in matches if match[1] >= 80), None)

    if best_match:
        # Troviamo il prodotto esatto
        matched_product = next(prod for prod in products if prod['name'] == best_match)
        return {
            "id": matched_product["id"],
            "name": matched_product["name"],
            "price": matched_product["list_price"]
        }
    
    # Se nessun match supera 90, filtra quelli con score > 50
    valid_matches = [match[0] for match in matches if match[1] > 45]

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


def generate_order(partner_id, order_lines, name, currency_id, company_id=1, user_id=2):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)
    print("Partner id", partner_id)
    print("Order lines", order_lines)
    print("Name", name)
    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    # Modelli Odoo
    PurchaseOrder = odoo.env['purchase.order']
    PurchaseOrderLine = odoo.env['purchase.order.line']

    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Creazione dell'ordine di acquisto
    order_id = PurchaseOrder.create({
        'partner_id': partner_id,
        'currency_id': currency_id,
        'company_id': company_id,
        'user_id': user_id,
        'company_id': company_id,
        'state': 'draft',
        'date_order': current_datetime,
        'amount_total': sum(qty * price for _, qty, price,_ in order_lines),
        'name': name,
    })

    order_lines_data = []

    # Creazione delle linee d'ordine
    for product_id, product_qty, price_unit, _ in order_lines:
        line_id = PurchaseOrderLine.create({
            'order_id': order_id,
            'product_id': product_id,
            'product_qty': product_qty,
            'price_unit': price_unit,
            'price_subtotal': product_qty * price_unit,
            'price_total': product_qty * price_unit,
            'date_planned': current_datetime,
        })

        # Salviamo i dettagli delle righe ordine
        order_lines_data.append({
            'line_id': line_id,
            'product_id': product_id,
            'product_qty': product_qty,
            'price_unit': price_unit,
            'price_subtotal': product_qty * price_unit,
            'quantity_received_manual': 0
        })

    # Recuperiamo i dettagli dell'ordine creato
    order_details = PurchaseOrder.browse(order_id)

    # Creiamo il dizionario con tutte le informazioni
    result = {
        "order_id": order_id,
        "name": order_details.name,
        "partner_id": order_details.partner_id.id if order_details.partner_id else None,
        "partner_name": order_details.partner_id.name if order_details.partner_id else None,
        "currency_id": order_details.currency_id.id if order_details.currency_id else None,
        "currency_name": order_details.currency_id.name if order_details.currency_id else None,
        "company_id": order_details.company_id.id if order_details.company_id else None,
        "company_name": order_details.company_id.name if order_details.company_id else None,
        "user_id": order_details.user_id.id if order_details.user_id else None,
        "user_name": order_details.user_id.name if order_details.user_id else None,
        "date_order": order_details.date_order,
        "amount_total": order_details.amount_total,
        "state": order_details.state,
        "order_lines": order_lines_data
    }

    return result





# def confirm_order(order_id):
#     odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario

#     # Autenticazione
#     db = 'db_test'
#     username = 'prova@prova'
#     password = 'password'
#     odoo.login(db, username, password)

#     PurchaseOrder = odoo.env['purchase.order']
#     StockMove = odoo.env['stock.move']

#     try:
#         order = PurchaseOrder.browse(order_id)
#         if not order.exists():
#             return f"Errore: Ordine ID {order_id} non trovato."

#         if order.state != 'draft':  # Assumiamo che 'draft' corrisponda a 'Bozza'
#             return f"Errore: Ordine ID {order_id} non in stato 'Bozza' ma '{order.state}'."

#         # Conferma l'ordine
#         order.write({
#             'state': 'purchase',
#             'date_approve': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         })

#         # Trova i movimenti di magazzino associati
#         moves = StockMove.search([('purchase_line_id', 'in', order.order_line.ids), ('state', '=', 'draft')])
#         print("MOVES: ", moves)
#         # Aggiorna lo stato dei movimenti di magazzino per essere conteggiati nella quantità prevista
#         if moves:
#             move_records = StockMove.browse(moves)
#             move_records.write({'state': 'assigned', 'location_final_id': 8, 'picking_id':16, 'group_id':4, 'picking_type_id':1, 'warehouse_id': 1, 'quantity':10, 'price_unit' : 1000 })  # Imposta lo stato come 'confirmed' senza modificare la quantità
        
#         return f"Successo: Ordine ID {order_id} confermato e movimenti di magazzino aggiornati."

#     except Exception as e:
#         return f"Errore: impossibile confermare l'ordine ID {order_id}. Dettaglio: {str(e)}"



def complete_order(order_id):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    
    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)
    
    PurchaseOrder = odoo.env['purchase.order']
    StockQuant = odoo.env['stock.quant']
    
    try:
        order = PurchaseOrder.browse(order_id)
        if not order.exists():
            return f"Errore: Ordine ID {order_id} non trovato."
        
        if order.state != 'purchase':  
            return f"Errore: Ordine ID {order_id} non in stato 'Acquistato' ma '{order.state}'."
        
        # Aggiorna direttamente la quantità disponibile dei prodotti in magazzino
        for line in order.order_line:
            product = line.product_id
            location_id = order.picking_type_id.default_location_dest_id.id  # Magazzino di destinazione
            
            if not location_id:
                return f"Errore: Nessun magazzino di destinazione trovato per l'ordine {order_id}."
            
            quant = StockQuant.search([('product_id', '=', product.id), ('location_id', '=', location_id)])
            
            if quant:
                quant_record = StockQuant.browse(quant[0])
                quant_record.write({'quantity': quant_record.quantity + line.product_qty})
            else:
                # Se non esiste una riga stock.quant per questo prodotto e magazzino, la creiamo
                StockQuant.create({
                    'product_id': product.id,
                    'location_id': location_id,
                    'quantity': line.product_qty
                })
        
        # Segna l'ordine come completato
        order.write({'state': 'done'})
        
        return f"Successo: Ordine ID {order_id} completato e quantità di prodotto aggiornata in magazzino."
    
    except Exception as e:
        return f"Errore: impossibile completare l'ordine ID {order_id}. Dettaglio: {str(e)}"


def delete_order(order_id):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    
    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)
    
    PurchaseOrder = odoo.env['purchase.order']
    
    try:
        order = PurchaseOrder.browse(order_id)
        if not order.exists():
            return f"Errore: Ordine ID {order_id} non trovato."
        
        if order.state != 'draft':  # Assumiamo che 'draft' corrisponda a 'Bozza'
            return f"Errore: Ordine ID {order_id} non in stato 'Bozza' ma '{order.state}'."
        
        # Conferma l'ordine
        order.write({
            'state': 'cancel',
        })
        return f"Successo: Ordine ID {order_id} cancellato con successo."
    
    except Exception as e:
        return f"Errore: impossibile cancellare l'ordine ID {order_id}. Dettaglio: {str(e)}"



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



