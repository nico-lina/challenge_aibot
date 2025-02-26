import pandas as pd
import odoorpc
import psycopg2 as psql
from datetime import datetime, timedelta
from rapidfuzz import process, fuzz
import random

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
    
    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    # Modelli Odoo
    PurchaseOrder = odoo.env['purchase.order']
    PurchaseOrderLine = odoo.env['purchase.order.line']

    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    random_days = random.randint(1, 10)
    date_scheduled = (datetime.now() + timedelta(days=random_days)).strftime('%Y-%m-%d %H:%M:%S')

    # Creazione dell'ordine di acquisto
    order_id = PurchaseOrder.create({
        'partner_id': partner_id,
        'currency_id': currency_id,
        'company_id': company_id,
        'user_id': user_id,
        'company_id': company_id,
        'state': 'draft',
        'date_order': current_datetime,
        'date_approve' : current_datetime,
        'amount_total': sum(qty * price for _, qty, price,_ in order_lines),
        'name': name,
        'date_planned': date_scheduled
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
            'date_planned': date_scheduled, 
        })

        # Salviamo i dettagli delle righe ordine
        order_lines_data.append({
            'line_id': line_id,
            'product_id': product_id,
            'product_qty': product_qty,
            'price_unit': price_unit,
            'price_subtotal': product_qty * price_unit,
            'quantity_received_manual': 0,
            'date_scheduled' : date_scheduled
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



#TODO creare campo expiration date e impostarlo, poi utilizzarlo per filtrare come parte della chiave primaria in stock quant
#TODO campi da usare date_order, date_approve, date_planned -> creo l'ordine, effective_date -> quando confermo
def complete_order(order_id):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    
    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)
    
    PurchaseOrder = odoo.env['purchase.order']
    StockQuant = odoo.env['stock.quant']
    StockMove = odoo.env['stock.move']
    StockProductionLot = odoo.env['stock.lot']  # Tabella per i lotti
    
    random_days = random.randint(90, 360)
    expiration_date = (datetime.now() + timedelta(days=random_days)).replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
    current_date = datetime.now().replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
    
    print("EXP DATE:", expiration_date)
    print("CURRENT_DATE:", current_date)

    order = PurchaseOrder.browse(order_id)
    if not order.exists():
        return f"Errore: Ordine ID {order_id} non trovato."
    
    if order.state != 'draft':  
        return f"Errore: Ordine ID {order_id} non in stato 'Draft' ma '{order.state}'."
    
    for line in order.order_line:
        product = line.product_id
        location_id = 4  # Location di partenza
        location_dest_id = 8  # Location di destinazione
        partner_id = order.partner_id.id
        product_uom_qty = line.product_qty
        
        # 🔹 CREAZIONE O RECUPERO DEL LOTTO
        lot = StockProductionLot.search([
            ('product_id', '=', product.id),
            ('expiration_date', '=', expiration_date)
        ], limit=1)

        if not lot:
            lot = StockProductionLot.create({
                'name': f"LOT-{product.id}-{random_days}",
                'product_id': product.id,
                'expiration_date': expiration_date
            })
        else:
            lot = StockProductionLot.browse(lot[0])
        print("LOT: ", lot)
        # 🔹 CREAZIONE O AGGIORNAMENTO DI StockQuant CON IL LOTTO
        quant = StockQuant.search([
            ('product_id', '=', product.id), 
            ('location_id', '=', location_dest_id), 
            ('lot_id', '=', lot)  # Collegamento corretto al lotto
        ])

        if quant:
            quant_record = StockQuant.browse(quant[0])
            quant_record.write({'quantity': quant_record.quantity + product_uom_qty})
        else:
            StockQuant.create({
                'product_id': product.id,
                'location_id': location_dest_id,
                'quantity': product_uom_qty,
                'lot_id': lot 
            })

        StockMove.create({
            'product_id': product.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'partner_id': partner_id,
            'product_uom_qty': product_uom_qty,
            'date': current_date,
            'name': f"Ordine {product.id}", 
        })
        
    order.write({
        'state': 'purchase',
        'effective_date': current_date
    })
    
    return f"Successo: Ordine ID {order_id} completato, quantità aggiornata e movimento di magazzino creato."



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
        
        if order.state != 'draft':  
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
        quants = StockQuant.search_read([('product_id', '=', product_id), ('quantity', '>=', 0)], ['quantity'])
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


def get_order_details(order_id):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario
    
    # Autenticazione
    db = 'db_test'
    username = 'prova@prova'
    password = 'password'
    odoo.login(db, username, password)

    # Modello Odoo
    PurchaseOrder = odoo.env['purchase.order']
    PurchaseOrderLine = odoo.env['purchase.order.line']
    
    # Recupero ordine
    order = PurchaseOrder.browse(order_id)
    if not order:
        return {"error": "Ordine non trovato"}
    
    # Recupero linee d'ordine
    order_lines_data = []
    for line in order.order_line:
        order_lines_data.append({
            'line_id': line.id,
            'product_id': line.product_id.id,
            'product_name': line.product_id.name,
            'product_qty': line.product_qty,
            'price_unit': line.price_unit,
            'price_subtotal': line.price_subtotal,
            'quantity_received_manual': line.quantity_received_manual
        })
    
    # Creazione del risultato
    result = {
        "order_id": order.id,
        "name": order.name,
        "partner_id": order.partner_id.id if order.partner_id else None,
        "partner_name": order.partner_id.name if order.partner_id else None,
        "currency_id": order.currency_id.id if order.currency_id else None,
        "currency_name": order.currency_id.name if order.currency_id else None,
        "company_id": order.company_id.id if order.company_id else None,
        "company_name": order.company_id.name if order.company_id else None,
        "user_id": order.user_id.id if order.user_id else None,
        "user_name": order.user_id.name if order.user_id else None,
        "date_order": order.date_order,
        "amount_total": order.amount_total,
        "state": order.state,
        "order_lines": order_lines_data
    }
    
    return result