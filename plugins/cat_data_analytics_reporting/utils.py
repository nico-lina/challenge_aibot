import pandas as pd
import odoorpc
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
from pathlib import Path
import math
from markdown import markdown
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import os
import time
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
import re
from bs4 import BeautifulSoup



# Connessione a Odoo
def connect_to_odoo():
    db = 'health_final'
    username = 'admin'
    password = 'admin'    
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)
    odoo.login(db, username, password)
    return odoo



# Dettaglio stock per prodotto
def get_stock_report():
    
    odoo = connect_to_odoo()
    
    Product = odoo.env['product.product']
    StockQuant = odoo.env['stock.quant']
    OrderPoint = odoo.env['stock.warehouse.orderpoint']
    ProductCategory = odoo.env['product.category']
    
    products = Product.search_read([('type', '=', 'consu')], ['id', 'name', 'categ_id', 'standard_price', 'default_code'])
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
        product_code = product['default_code']
        product_code = product_code if product_code else "Non Disponibile"

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
            'Codice Prodotto': product_code,
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

    moves = StockMove.search_read([], ['product_id', 'date', 'location_dest_id', 'product_uom_qty', 'partner_id'])
    
    data = []

    for move in moves:
        product_id = move['product_id'][0] if move['product_id'] else 'Sconosciuto'
        products = Product.search_read([("id", "=", product_id)], ['name', 'categ_id', 'default_code'])
        product_name = products[0]['name']
        product_category = products[0]['categ_id'][1] if products[0]['categ_id'] else 'Sconosciuta'
        product_code = products[0]['default_code']
        product_code = product_code if product_code else "Non Disponibile"

        locations = Location.search_read([("id", "=", move['location_dest_id'][0])], ['id', 'usage'])
        location = locations[0]
        movement_type = '🟢 Entrata' if location['usage'] == 'internal' else '🔴 Uscita'

        # Convertire la stringa in un oggetto datetime
        move_date = datetime.strptime(move['date'], "%Y-%m-%d %H:%M:%S")

        # Estrarre solo il giorno
        move_date = move_date.date()

        if move['partner_id']:
            # Usa l'ID del partner invece del nome
            stk_id = move['partner_id'][0]

            # Ottenere più informazioni sul partner
            stakeholders = Stakeholder.search_read([("id", "=", stk_id)], ['name', 'street', 'email'])
            stakeholder_name = stakeholders[0]['name']
            stakeholder_address = stakeholders[0].get('street', 'Non disponibile')
            stakeholder_email = stakeholders[0].get('email', 'Non disponibile')
        else:
            stakeholder_name = "Non disponibile"
            stakeholder_address = "Non disponibile"
            stakeholder_email = "Non disponibile" 

        data.append({
            'Nome del Prodotto': product_name,
            'Codice del Prodotto': product_code,
            'Categoria Prodotto': product_category,
            'Data': move_date,
            'Tipo Movimento': movement_type,
            'Quantità': move['product_uom_qty'],
            'Fornitore': stakeholder_name,
            'Indirizzo Fornitore': stakeholder_address,
            'Email Fornitore': stakeholder_email,
        })

    df = pd.DataFrame(data)

    df_markdown = df.to_markdown(index=False)

    return df_markdown, df


# Aggiungere l'indicatore di performance nella stessa colonna
def get_performance_indicator(days):
    if days <= 0:
        return f"🟢 Buono"
    elif days <= 5:
        return "🟠 Migliorabile"
    else:
        return "🔴 Critico"


def get_supplier_performance_data():
    odoo = connect_to_odoo()

    Purchase = odoo.env['purchase.order']
    Supplier = odoo.env['res.partner']
    Product = odoo.env['product.product']
    OrderLine = odoo.env['purchase.order.line']

    # Estrazione degli ordini di acquisto completati e ricevuti (state = done)
    purchase_orders = Purchase.search_read([('state', 'in', ['done', 'purchase'])], ['name', 'partner_id', 'order_line', 'effective_date', 'date_planned', 'date_order'])

    data = []
    print("PURCHASE ORDER: ",purchase_orders)
    for order in purchase_orders:
        print("ORDER", order)
        # Ottenere i dettagli del fornitore
        supplier_id = order['partner_id'][0]
        supplier_data = Supplier.search_read([('id', '=', supplier_id)], ['name', 'email'])
        supplier_info = supplier_data[0]
        print("SUPPLIER INFO:", supplier_info)
    
        for line_id in order['order_line']:
            lines = OrderLine.search_read([('id', '=', line_id)], ['product_id', 'product_qty', 'price_unit', 'price_total'])
            line = lines[0]

            product_data = Product.search_read([('id', '=', line['product_id'][0])], ['name'])

            date_order = datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S')
            date_planned = datetime.strptime(order['date_planned'], '%Y-%m-%d %H:%M:%S')
            effective_date = datetime.strptime(order['effective_date'], '%Y-%m-%d %H:%M:%S') if order['effective_date'] else None
            print("DATE ORDER: ", date_order)
            print("DATE PLANNED: ", date_planned)
            print ("EFFECTIVE DATE", effective_date)
            # Calcolo del ritardo di consegna
            if date_planned:
                if effective_date is not None:
                    delay = max((effective_date - date_planned).days, 0)  # Ritardo solo se > 0
                else:
                    today = datetime.today()
                    delay = max((today - date_planned).days, 0)
            else:
                delay = float('inf')  # Caso critico se manca la data prevista

            # calcolo tempo medio di consegna
            if date_planned:
                if effective_date:
                        delivery_time = (effective_date - date_order).days
                else:
                    today = datetime.today()
                    delivery_time = (today - date_order).days
            else:
                # Se non ci sono pickings, impostiamo il ritardo come critico
                delivery_time = float('inf')
            # Aggiungi ai dati
            data.append({
                'Fornitore': supplier_info['name'],
                'Prodotto': product_data[0]['name'],
                'Quantità': line['product_qty'],
                'Prezzo Totale': line['price_total'],
                'Tempo di Consegna (giorni)': delivery_time,
                'Ritardo di Consegna (giorni)': delay
            })


    df = pd.DataFrame(data)
    #Aggiunta gestione db vuoto
    if df.empty : 
        return "null", df
    # Calcolare le performance
    df['Tempo di Consegna (giorni)'] = df['Tempo di Consegna (giorni)'].fillna(0)  # Gestione dei valori nulli
    
    # Calcolare performance aggregate per fornitore
    performance = df.groupby('Fornitore').agg({
        'Tempo di Consegna (giorni)': 'mean',
        'Quantità': 'sum',
        'Prezzo Totale': 'sum',
        'Ritardo di Consegna (giorni)': 'mean'
    }).reset_index()

    performance['Performance'] = performance['Tempo di Consegna (giorni)'].apply(get_performance_indicator)

    performance_markdown = performance.to_markdown(index=False)
    df_markdown = df.to_markdown(index=False)


    return df_markdown, performance_markdown



# Funzione per generare il report
def generate_warehouse_report():

    stock, _ = get_stock_report()
    stock_movement, _ = get_stock_movements()
    _, supplier = get_supplier_performance_data()

    return stock, stock_movement, supplier


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
    html_text = markdown(markdown_text)
    soup = BeautifulSoup(html_text, "html.parser")

    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pdf_filename = f"{file_name}_{current_time}.pdf"

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    output_dir = os.path.join(base_dir, "static")

    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, pdf_filename)

    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter), leftMargin=20, rightMargin=20)
    styles = getSampleStyleSheet()
    story = []

    def parse_markdown_table(text):
        lines = text.strip().split('\n')
        table_data = []
        for line in lines:
            if '|' in line and not line.startswith('|:'):  # Ignora la riga dei trattini
                row = [col.strip() for col in line.split('|')[1:-1]]
                if row:
                    table_data.append(row)
        return table_data

    def parse_table(text):
        table_data = parse_markdown_table(text)

        if table_data:
            col_widths = [80] * len(table_data[0])
            table = Table(table_data, repeatRows=1, colWidths=col_widths, hAlign='CENTER')
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("WORDWRAP", (0, 0), (-1, -1), 'CJK'),  # Wrapping per testo lungo
            ]))

            for i, row in enumerate(table_data[1:], start=1):
                if len(row) >= 7:
                    stato = row[6]
                    color = colors.black
                    if '🔴' in stato:
                        color = colors.red
                    elif '🟠' in stato:
                        color = colors.orange
                    elif '🟢' in stato:
                        color = colors.green
                    table.setStyle([("TEXTCOLOR", (6, i), (6, i), color)])

            story.append(table)
            story.append(Spacer(1, 12))

    def parse_list(element):
        items = [li.get_text(strip=True) for li in element.find_all("li")]
        if items:
            for item in items:
                if '🔴' in item:
                    story.append(Paragraph(f'<font color="red">• {item}</font>', styles["Normal"]))
                elif '🟠' in item:
                    story.append(Paragraph(f'<font color="orange">• {item}</font>', styles["Normal"]))
                elif '🟢' in item:
                    story.append(Paragraph(f'<font color="green">• {item}</font>', styles["Normal"]))
                else:
                    story.append(Paragraph(f"• {item}", styles["Normal"]))
            story.append(Spacer(1, 12))

    table_pattern = re.compile(r'(\|.*\|\n)+')

    for element in soup.find_all(["h1", "h2", "h3", "p", "ul", "li"]):
        text = element.get_text(strip=True)

        if element.name == "p" and table_pattern.search(text):
            parse_table(text)

        elif element.name == "ul":
            parse_list(element)

        else:
            if element.name == "h1":
                story.append(Paragraph(text, styles["Title"]))
            elif element.name == "h2":
                story.append(Paragraph(text, styles["Heading1"]))
            elif element.name == "h3":
                story.append(Paragraph(text, styles["Heading2"]))
            else:
                story.append(Paragraph(text, styles["Normal"]))
            story.append(Spacer(1, 12))

    doc.build(story)
    print(f"✅ PDF creato: {pdf_path}")