import pandas as pd
import odoorpc
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
from pathlib import Path
import math
from markdown import markdown
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import os
import time



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
    Product = odoo.env['product.product']
    Stakeholder = odoo.env['res.partner']
    Location = odoo.env['stock.location']

    moves = StockMove.search_read([], ['product_id', 'date', 'location_id', 'location_dest_id', 'product_uom_qty', 'partner_id'])
    
    data = []

    for move in moves:
        print("Move:", move)
        product_id = move['product_id'][0] if move['product_id'] else 'Sconosciuto'
        print("Product ID:", product_id)
        products = Product.search_read([("id", "=", product_id)], ['name', 'categ_id'])
        print("Products", products)
        product_name = products[0]['name']
        product_category = products[0]['categ_id'][1] if products[0]['categ_id'] else 'Sconosciuta'

        print(move['location_dest_id'][0])
        locations = Location.search_read([("id", "=", move['location_dest_id'][0])], ['id', 'usage'])
        location = locations[0]
        print("Location Dest:", location)
        movement_type = '🟢 Entrata' if location['usage'] == 'internal' else '🔴 Uscita'

        print("mov type:", movement_type)

        # Convertire la stringa in un oggetto datetime
        move_date = datetime.strptime(move['date'], "%Y-%m-%d %H:%M:%S")

        # Estrarre solo il giorno
        move_date = move_date.date()

        print("Data:", move['date'])
        print("Data:", type(move['date']))
        print("Data:", move_date)

        if move['partner_id']:
            # Usa l'ID del partner invece del nome
            stk_id = move['partner_id'][0]

            print("Stk id:", stk_id)

            # Ottenere più informazioni sul partner
            stakeholders = Stakeholder.search_read([("id", "=", stk_id)], ['name', 'street', 'email'])
            stakeholder_name = stakeholders[0]['name']
            stakeholder_address = stakeholders[0].get('street', 'Non disponibile')
            stakeholder_email = stakeholders[0].get('email', 'Non disponibile')
            print(stakeholders)
        else:
            stakeholder_name = "Non disponibile"
            stakeholder_address = "Non disponibile"
            stakeholder_email = "Non disponibile" 

        data.append({
            'Prodotto ID': product_id,
            'Nome del Prodotto': product_name,
            'Categoria Prodotto': product_category,
            'Data': move_date,
            'Tipo Movimento': movement_type,
            'Quantità': move['product_uom_qty'],
            'Fornitore': stakeholder_name,
            'Indirizzo Fornitore': stakeholder_address,
            'Email Fornitore': stakeholder_email,
        })

    df = pd.DataFrame(data)
    df = df.sort_values(by='Data')

    df_markdown = df.to_markdown(index=False)

    return df_markdown, df


def get_supplier_performance_data_2():
    try:
        odoo = connect_to_odoo()

        Purchase = odoo.env['purchase.order']
        Supplier = odoo.env['res.partner']
        Product = odoo.env['product.product']
        OrderLine = odoo.env['purchase.order.line']

        # Estrazione degli ordini di acquisto completati o confermati
        purchase_orders = Purchase.search_read(
            [("state", "in", ['purchase', 'done'])], 
            ['partner_id', 'date_order', 'date_approve', 'order_line', 'state']
        )

        data = []

        for order in purchase_orders:
            # Dettagli fornitore
            supplier_id = order['partner_id'][0]
            supplier_data = Supplier.search_read([('id', '=', supplier_id)], ['name', 'email'])
            supplier_info = supplier_data[0] if supplier_data else {'name': 'Sconosciuto', 'email': 'N/A'}

            order_lines = []
            for line_id in order['order_line']:
                lines = OrderLine.search_read([('id', '=', line_id)], 
                                              ['product_id', 'product_qty', 'price_unit', 'price_total'])
                if not lines:
                    continue

                line = lines[0]
                product_data = Product.search_read([('id', '=', line['product_id'][0])], ['name'])
                product_name = product_data[0]['name'] if product_data else 'Prodotto Sconosciuto'

                order_lines.append({
                    'product_name': product_name,
                    'product_price': line['price_unit'],
                    'quantity': line['product_qty'],
                    'subtotal': line['price_total']
                })

            date_order = datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S')
            date_approve = datetime.strptime(order['date_approve'], '%Y-%m-%d %H:%M:%S') if order['date_approve'] else date_order
            delivery_time = max((date_approve - date_order).days, 0)

            for line in order_lines:
                data.append({
                    'Fornitore': supplier_info['name'],
                    'Email Fornitore': supplier_info.get('email', 'N/A'),
                    'Prodotto': line['product_name'],
                    'Quantità': line['quantity'],
                    'Prezzo': line['product_price'],
                    'Totale Ordine': line['subtotal'],
                    'Data Ordine': date_order,
                    'Data Approvazione': date_approve,
                    'Tempo di Consegna (giorni)': delivery_time,
                    'Stato Ordine': order['state'],  # Nuova colonna per lo stato
                })

        # Creazione del DataFrame
        df = pd.DataFrame(data)

        # Calcolare performance aggregate per fornitore
        performance = df.groupby('Fornitore').agg({
            'Totale Ordine': 'sum',
            'Tempo di Consegna (giorni)': 'mean',
            'Quantità': 'sum',
        }).reset_index()

        # Calcolare performance aggregate per fornitore
        performance = df.groupby('Fornitore').agg({
            'Totale Ordine': 'sum',
            'Tempo di Consegna (giorni)': 'mean',
            'Quantità': 'sum',
        }).reset_index()

        # Aggiungere l'indicatore di performance
        def get_performance_indicator(days):
            if days <= 0:
                return '🟢'  # Buono
            elif days <= 5:
                return '🟠'  # Migliorabile
            else:
                return '🔴'  # Critico

        performance['Performance'] = performance['Tempo di Consegna (giorni)'].apply(get_performance_indicator)

        performance = performance.sort_values(by='Tempo di Consegna (giorni)')

        # Generazione del markdown per la visualizzazione
        performance_markdown = performance.to_markdown(index=False)

        return performance_markdown, performance

    except Exception as e:
        print(f"Errore durante l'estrazione delle performance dei fornitori: {e}")
        return None, None




def get_supplier_performance_data():
    odoo = connect_to_odoo()

    Purchase = odoo.env['purchase.order']
    Supplier = odoo.env['res.partner']
    Product = odoo.env['product.product']
    OrderLine = odoo.env['purchase.order.line']
    StockPicking = odoo.env['stock.picking']

    # Estrazione degli ordini di acquisto completati o confermati
    purchase_orders = Purchase.search_read(
        [("state", "in", ['purchase', 'done', 'sent'])], 
        ['name', 'partner_id', 'date_order', 'date_approve', 'order_line', 'state']
    )
    data = []

    for order in purchase_orders:
        print("Purchase order:", order)

        # Ottenere i dettagli del fornitore
        supplier_id = order['partner_id'][0]
        supplier_data = Supplier.search_read([('id', '=', supplier_id)], ['name', 'email'])
        supplier_info = supplier_data[0]

        print("Supplier:", supplier_data)

        for line_id in order['order_line']:
            lines = OrderLine.search_read([('id', '=', line_id)], ['product_id', 'product_qty', 'price_unit', 'price_total'])
            line = lines[0]

            product_data = Product.search_read([('id', '=', line['product_id'][0])], ['name'])

            date_order = datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S')
            date_approve = datetime.strptime(order['date_approve'], '%Y-%m-%d %H:%M:%S') if order['date_approve'] else date_order
            
            # Recupero della data di consegna effettiva da stock.picking
            pickings = StockPicking.search_read(
                [('origin', '=', order['name'])], 
                ['date_done', 'scheduled_date']
            )

            print(f"Pickings for Order {order['name']}: {pickings}")

            # Calcolo del tempo di consegna o del ritardo
            if pickings:
                date_done = pickings[0].get('date_done')
                scheduled_date = pickings[0].get('scheduled_date')
                
                if date_done:
                    # Se la consegna è stata effettuata
                    date_done = datetime.strptime(date_done, '%Y-%m-%d %H:%M:%S')
                    delivery_time = (date_done - date_order).days
                elif scheduled_date:
                    # Se non c'è data_done, calcolo del ritardo
                    scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%d %H:%M:%S')
                    delivery_time = (scheduled_date - date_order).days
                else:
                    # Se non ci sono date, impostiamo il ritardo come critico
                    delivery_time = float('inf')  # Rappresenta un ritardo critico
            else:
                # Se non ci sono pickings, impostiamo il ritardo come critico
                delivery_time = float('inf')

            # Aggiungi ai dati
            data.append({
                'Fornitore': supplier_info['name'],
                'Email Fornitore': supplier_info['email'],
                'Prodotto': product_data[0]['name'],
                'Quantità': line['product_qty'],
                'Prezzo': line['price_unit'],
                'Totale Ordine': line['price_total'],
                'Data Ordine': date_order,
                'Data Approvazione': date_approve,
                'Data Done': data_done,
                'Tempo di Consegna (giorni)': delivery_time,
            })


    df = pd.DataFrame(data)

    # Calcolare le performance
    df['Tempo di Consegna (giorni)'] = df['Tempo di Consegna (giorni)'].fillna(0)  # Gestione dei valori nulli

    print("Total df: ", data)
    
    # Calcolare performance aggregate per fornitore
    performance = df.groupby('Fornitore').agg({
        'Totale Ordine': 'sum',
        'Tempo di Consegna (giorni)': 'mean',
        'Quantità': 'sum',
    }).reset_index()

    # Aggiungere l'indicatore di performance nella stessa colonna
    def get_performance_indicator(days):
        if days <= 0:
            return f"Buono 🟢"
        elif days <= 5:
            return "Migliorabile 🟠"
        else:
            return "Critico 🔴"

    performance['Performance'] = performance['Tempo di Consegna (giorni)'].apply(get_performance_indicator)

    performance_markdown = performance.to_markdown(index=False)
    df_markdown = df.to_markdown(index=False)
    return df_markdown, performance



# Funzione per generare il report
def generate_warehouse_report():

    overview, _ = get_stock_overview()
    stock, _ = get_stock_report()
    stock_movement, _ = get_stock_movements()
    supplier, _ = get_supplier_performance_data()

    return overview, stock, stock_movement, supplier


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


def write_pdf(markdown_text, file_name):
    # Converti il Markdown in HTML
    html_text = markdown(markdown_text)

    # Ottieni la data e ora corrente
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pdf_filename = f"{file_name}_{current_time}.pdf"

    # Percorso corretto per salvare i PDF
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))  # Sale fino a challenge_aibot
    output_dir = os.path.join(base_dir, "static")
    os.makedirs(output_dir, exist_ok=True)  # Crea la cartella se non esiste
    pdf_path = os.path.join(output_dir, pdf_filename)

    # Creazione del documento PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Separiamo il testo in righe per individuare la tabella
    lines = html_text.split("\n")
    table_data = []
    inside_table = False

    for line in lines:
        if line.startswith("|"):  # Riconosce le righe della tabella Markdown
            table_data.append(line.strip().split("|")[1:-1])  # Rimuove i bordi "|"
            inside_table = True
        elif inside_table:
            break  # Fine della tabella

    if table_data:
        # Applica uno stile alla tabella
        table = Table(table_data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),  # Intestazione grigia
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

    # Aggiunge il resto del testo che non è nella tabella
    for line in lines:
        if not line.startswith("|"):  # Evita di aggiungere due volte le righe della tabella
            story.append(Paragraph(line, styles["Normal"]))
            story.append(Spacer(1, 12))

    # Creazione del PDF
    doc.build(story)
    print(f"✅ PDF creato: {pdf_path}")
