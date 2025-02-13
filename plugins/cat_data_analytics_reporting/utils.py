import pandas as pd
import odoorpc
import matplotlib.pyplot as plt

# Connessione a Odoo
def connect_to_odoo():
    db = 'test'
    username = 'admin'
    password = 'admin'    
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)
    odoo.login(db, username, password)
    return odoo


# Panoramica generale dello stock
def get_stock_overview():

    odoo = connect_to_odoo()
    
    Product = odoo.env['product.product']
    StockQuant = odoo.env['stock.quant']
    
    products = Product.search_read([], ['id', 'name', 'standard_price'])
    quants = StockQuant.search_read([], ['product_id', 'quantity'])

    total_products = len(products)
    total_stock_value = sum(p['standard_price'] * q['quantity'] for p in products for q in quants if q['product_id'] and q['product_id'][0] == p['id'])
    total_quantity = sum(q['quantity'] for q in quants)

    data = [{
        "Totale Prodotti": total_products,
        "Quantità Totale Disponibile": total_quantity,
        "Valore Totale Stock (€)": round(total_stock_value, 2)
    }]

    df = pd.DataFrame(data)
    
    return df


# Dettaglio stock per prodotto
def get_stock_report():
    
    odoo = connect_to_odoo()
    
    Product = odoo.env['product.product']
    StockQuant = odoo.env['stock.quant']
    
    products = Product.search_read([], ['id', 'name', 'categ_id', 'standard_price'])
    quants = StockQuant.search_read([], ['product_id', 'location_id', 'quantity'])
    
    stock_data = {}
    for quant in quants:
        product_id = quant['product_id'][0] if quant['product_id'] else None
        if product_id:
            stock_data.setdefault(product_id, 0)
            stock_data[product_id] += quant['quantity']

    data = []
    for product in products:
        product_id = product['id']
        product_name = product['name']
        category = product['categ_id'][1] if product['categ_id'] else 'Sconosciuto'
        price = product['standard_price']
        quantity = stock_data.get(product_id, 0)
        total_value = quantity * price

        data.append({
            'Prodotto': product_name,
            'Categoria': category,
            'Quantità Disponibile': quantity,
            'Prezzo Unitario (€)': price,
            'Valore Totale (€)': total_value
        })

    df = pd.DataFrame(data)

    return df


# Analisi livelli di stock
def get_low_stock_alerts():
    
    odoo = connect_to_odoo()
    
    Product = odoo.env['product.product']
    StockQuant = odoo.env['stock.quant']
    
    products = Product.search_read([], ['id', 'name', 'low_stock_threshold'])
    quants = StockQuant.search_read([], ['product_id', 'quantity'])
    
    stock_data = {q['product_id'][0]: q['quantity'] for q in quants if q['product_id']}
    
    data = []
    for product in products:
        product_id = product['id']
        # threshold = product.get('low_stock_threshold', 10)  # Default a 10 se non esiste
        quantity = stock_data.get(product_id, 0)
        status = '🟢 OK' if quantity >= threshold else ('🟠 Attenzione' if quantity > 0 else '🔴 Critico')

        data.append({
            'Prodotto': product['name'],
            'Quantità Disponibile': quantity,
            # 'Soglia Minima': threshold,
            'Stato Stock': status
        })

    df = pd.DataFrame(data)
    
    return df


# Movimenti di magazzino (entrate/uscite)
def get_stock_movements():

    odoo = connect_to_odoo()
    
    StockMove = odoo.env['stock.move']
    
    moves = StockMove.search_read([], ['product_id', 'date', 'location_id', 'location_dest_id', 'product_uom_qty'])
    
    data = []
    for move in moves:
        product = move['product_id'][1] if move['product_id'] else 'Sconosciuto'
        movement_type = 'Entrata' if move['location_id'] and move['location_dest_id'] else 'Uscita'
        
        data.append({
            'Data': move['date'],
            'Prodotto': product,
            'Tipo Movimento': movement_type,
            'Quantità': move['product_uom_qty']
        })

    df = pd.DataFrame(data)

    return df


# Funzione per generare il report
def generate_warehouse_report():

    overview = get_stock_overview()
    stock = get_stock_report()
    low_stock_alert = get_low_stock_alerts()
    stock_movement = get_stock_movements()

    return overview, stock, low_stock_alert, stock_movement








# Analisi del valore dello stock nel tempo
def plot_stock_trend():
    odoo = connect_to_odoo()
    
    StockHistory = odoo.env['stock.history']
    
    history = StockHistory.search_read([], ['date', 'value'])
    
    dates = [h['date'] for h in history]
    values = [h['value'] for h in history]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, values, marker='o', linestyle='-')
    plt.xlabel('Data')
    plt.ylabel('Valore Stock (€)')
    plt.title('Andamento Valore Stock nel Tempo')
    plt.xticks(rotation=45)
    plt.grid()
    plt.show()