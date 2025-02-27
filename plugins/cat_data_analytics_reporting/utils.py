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
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import re
from bs4 import BeautifulSoup
from reportlab.lib.units import cm



# Connessione a Odoo
def connect_to_odoo():
    db = 'test'
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
            'Quantità': quantity,
            'Stato': status,
            'Prezzo Unitario (€)': price,
            'Prezzo Totale (€)': total_value,
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

    for order in purchase_orders:

        # Ottenere i dettagli del fornitore
        supplier_id = order['partner_id'][0]
        supplier_data = Supplier.search_read([('id', '=', supplier_id)], ['name', 'email'])
        supplier_info = supplier_data[0]

        for line_id in order['order_line']:
            lines = OrderLine.search_read([('id', '=', line_id)], ['product_id', 'product_qty', 'price_unit', 'price_total'])
            line = lines[0]

            product_data = Product.search_read([('id', '=', line['product_id'][0])], ['name'])

            date_order = datetime.strptime(order['date_order'], '%Y-%m-%d %H:%M:%S')
            date_planned = datetime.strptime(order['date_planned'], '%Y-%m-%d %H:%M:%S')
            effective_date = datetime.strptime(order['effective_date'], '%Y-%m-%d %H:%M:%S') if order['effective_date'] else None

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
                'Tempo di Consegna': delivery_time,
                'Ritardo di Consegna': delay
            })


    df = pd.DataFrame(data)

    # Calcolare le performance
    df['Tempo di Consegna'] = df['Tempo di Consegna'].fillna(0)  # Gestione dei valori nulli
    
    # Calcolare performance aggregate per fornitore
    performance = df.groupby('Fornitore').agg({
        'Quantità': 'sum',
        'Prezzo Totale': 'sum',
        'Tempo di Consegna': 'mean',
        'Ritardo di Consegna': 'mean'
    }).reset_index()

    performance['Performance'] = performance['Tempo di Consegna'].apply(get_performance_indicator)

    performance_markdown = performance.to_markdown(index=False)

    return performance_markdown, performance



# Funzione per generare il report
def generate_warehouse_report():

    stock, _ = get_stock_report()
    stock_movement, _ = get_stock_movements()
    supplier, _ = get_supplier_performance_data()

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

    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pdf_filename = f"{file_name}_{current_time}.pdf"

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    output_dir = os.path.join(base_dir, "static")
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, pdf_filename)

    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter), leftMargin=20, rightMargin=20)

    # Converti il testo Markdown in HTML
    html_text = markdown(markdown_text)

    # Usa BeautifulSoup per analizzare l'HTML
    soup = BeautifulSoup(html_text, "html.parser")

    # Definizione della lista per i contenuti del PDF
    story = []
    styles = getSampleStyleSheet()
    heading_style = styles['Heading1']
    subheading_style = styles['Heading2']
    subsubheading_style = styles['Heading3']
    normal_style = ParagraphStyle(
            "Normal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=12,  # Modifica la dimensione del font
            leading=18,
            textColor=(0, 0, 0),  # Colore del testo (nero)
        )

    print("HTML: ", html_text)
    table_pattern = re.compile(r'(\|.*\|\n)+')


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

        styleN = styles['Normal']
        styleN.fontSize = 8  # Imposta una dimensione del font più piccola

        # Convert long text cells into Paragraphs for wrapping
        for row in table_data[1:]:
            for i in range(len(row)):
                if len(row[i]) > 15:  # Example threshold for long text
                    row[i] = Paragraph(row[i], styleN)

        num_cols = len(table_data[0])

        # Larghezza delle colonne adattabile
        max_width = A4[0] - 0.5 * cm  # Larghezza massima della pagina meno margini
        col_widths = [max_width / num_cols] * num_cols  # Larghezza uniforme

        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Stile migliorato per evitare il testo fuoriuscente
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),  # Testo più piccolo
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("WORDWRAP", (0, 0), (-1, -1), "CJK"),  # Word wrap attivato
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            # Impostazioni specifiche per l'intestazione
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Grassetto per l'intestazione
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7AC4FF")),  # sfondo azzurro per l'header 
        ]))

        story.append(Spacer(1, 12))
        story.append(table)
        story.append(Spacer(1, 12))


    def parse_list(element):
        items = [li.get_text(strip=True) for li in element.find_all("li")]
        if items:
            for item in items:
                item = item.replace(':', ': ')  # Aggiunge spazio dopo i due punti
                story.append(Paragraph(f"• {item}", styles["Normal"]))

            story.append(Spacer(1, 12))


    # Scorri tutti gli elementi HTML rilevanti
    for element in soup.find_all(["h1", "h2", "h3", "p", "ul", "li"]):
        text = element.get_text(strip=True)

        if element.name == "p" and table_pattern.search(text):
            parse_table(text)

        elif element.name == "ul":
            # For lists, process each list item
            for li in element.find_all('li'):
                story.append(Spacer(1, 6))
                story.append(Paragraph(f"• {li.text}", normal_style))
        else:
            if element.name == "h1":
                story.append(Spacer(1, 8))
                story.append(Paragraph(f"<font size=14>{element.text}</font>", heading_style))
            elif element.name == "h2":
                story.append(Spacer(1, 8))
                story.append(Paragraph(f"<font size=12>{element.text}</font>", subheading_style))
            elif element.name == "h3":
                story.append(Spacer(1, 8))
                story.append(Paragraph(f"<font size=10>{element.text}</font>", subsubheading_style))
            elif element.name == "p":
                story.append(Spacer(1, 6))
                story.append(Paragraph(element.text, normal_style))

    doc.build(story)
    print(f"✅ PDF creato: {pdf_path}")


