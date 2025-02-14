import pandas as pd
import odoorpc
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
from pathlib import Path
import math



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

    df_markdown = df.to_markdown(index=False)
    
    return df_markdown, df


# Dettaglio stock per prodotto
def get_stock_report():
    
    odoo = connect_to_odoo()
    
    Product = odoo.env['product.product']
    StockQuant = odoo.env['stock.quant']
    OrderPoint = odoo.env['stock.warehouse.orderpoint']
    ProductCategory = odoo.env['product.category']
    
    products = Product.search_read([], ['id', 'name', 'categ_id', 'standard_price'])
    quants = StockQuant.search_read([('quantity', '>=', 0)], ['product_id', 'location_id', 'quantity'])
    
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

        # Recupera l'ID della categoria
        categ_id = product['categ_id'][0] if product['categ_id'] else None

        # Recupera il nome della categoria dalla tabella 'product.category'
        if categ_id:
            category_data = ProductCategory.search_read([('id', '=', categ_id)], ['name'])
            if category_data:
                category = category_data[0]['name']

        price = product['standard_price']
        quantity = stock_data.get(product_id, 0)
        total_value = quantity * price

        # Recupera la quantità minima per il prodotto
        min_quantity_data = OrderPoint.search_read([('product_id', '=', product_id)], ['product_min_qty'])
        min_quantity = min_quantity_data[0]['product_min_qty'] if min_quantity_data else 0
        
        # Recupera la quantità disponibile dal dizionario stock_data
        quantity = stock_data.get(product_id, 0)

        threshold = min_quantity * 1.2 # il 20%
        threshold_rounded = math.ceil(threshold)

        # Determina il livello di criticità
        if quantity < min_quantity or quantity == 0:
            criticality_level = 'high'
        elif quantity <= threshold:  # Maggiore del minimo, ma sotto il 20% sopra
            criticality_level = 'medium'
        else:
            criticality_level = 'low'

        status = '🟢 OK' if criticality_level == "low" else ('🟠 Attenzione' if criticality_level == "medium" else '🔴 Critico')

        data.append({
            'Nome Prodotto': product_name,
            'Categoria': category,
            'Quantità Disponibile': quantity,
            'Soglia Minima': min_quantity,
            'Threshold': threshold_rounded,
            'Stato': status,
            'Prezzo Unitario (€)': price,
            'Valore Totale (€)': total_value,
        })

    df = pd.DataFrame(data)

    df_markdown = df.to_markdown(index=False)

    return df_markdown, df


# Movimenti di magazzino (entrate/uscite)
def get_stock_movements():

    odoo = connect_to_odoo()
    
    StockMove = odoo.env['stock.move']
    Product = odoo.env['product.template']
    Stakeholder = odoo.env['res.partner']
    Location = odoo.env['stock.location']

    moves = StockMove.search_read([], ['product_id', 'date', 'location_id', 'location_dest_id', 'product_uom_qty', 'partner_id'])
    
    data = []
    for move in moves:
        print("Move:", move)
        product_id = move['product_id'][0] if move['product_id'] else 'Sconosciuto'
        print("Product ID:", product_id)
        products = Product.search_read([("id", "=", product_id)], ['name'])
        print("Products", products)
        product_name = products[0]['name']

        locations = Location.search_read([("id", "=", move['location_dest_id'])], ['id', 'usage'])
        location = locations[0]
        movement_type = 'Entrata' if location['usage'] == 'internal' else 'Uscita'

        if movement_type == 'Entrata':
            stk_id = move['partner_id'][1] if move['partner_id'] else 'Sconosciuto'

            stakeholders = Stakeholder.search_read([("id", "=", stk_id)], ['name'])
            stakeholder_name = stakeholders[0]['name']
        else:
            stakeholder_name = 'Non Disponibile'
        
        
        data.append({
            'Prodotto ID': product_id,
            'Nome del Prodotto': product_name,
            'Data': move['date'],
            'Tipo Movimento': movement_type,
            'Quantità': move['product_uom_qty'],
            'Fornitore': stakeholder_name
        })

    df = pd.DataFrame(data)

    df_markdown = df.to_markdown(index=False)

    return df_markdown, df


# Funzione per generare il report
def generate_warehouse_report():

    overview, _ = get_stock_overview()
    stock, _ = get_stock_report()
    stock_movement, _ = get_stock_movements()

    return overview, stock, stock_movement




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



def write_pdf(data, file_name):

    # Crea un'istanza di FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Carica un font che supporta Unicode
    pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
    pdf.set_font('DejaVu', '', 10)
    # pdf.set_font("Arial", size=10)

    # Impostare il margine orizzontale per il testo
    pdf.set_left_margin(5)
    pdf.set_right_margin(5)
    
    # Scrivi l'output nel PDF, suddividendolo per linee
    lines = data.split('\n')
    for line in lines:
        pdf.multi_cell(200, 10, line)
    
    # Ottieni la data e ora corrente
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    pdf_file_name = f"{file_name}_{current_time}"

    # Trova il percorso della directory corrente (utils)
    current_dir = Path(__file__).resolve().parent

    # Vai su di due livelli e accedi a static
    static_dir = current_dir.parent.parent / 'static'

    # Percorso completo per il file PDF
    pdf_file_path = static_dir / pdf_file_name

    # Salva il PDF in static
    pdf.output(str(pdf_file_path))

    print(f"PDF salvato come {pdf_file_name}.pdf")
