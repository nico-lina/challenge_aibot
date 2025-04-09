import pandas as pd
import odoorpc
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
from pathlib import Path
import math
from markdown import markdown
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
import os
import time
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import re
from bs4 import BeautifulSoup
from reportlab.lib.units import cm
import seaborn as sns
import matplotlib.dates as mdates



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
            'Data': move_date,
            'Tipo Movimento': movement_type,
            'Quantità': move['product_uom_qty'],
            'Fornitore': stakeholder_name,
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
    #Aggiunta gestione db vuoto
    if df.empty : 
        return "null", df
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



def create_file_path(file_name, ext):

    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pdf_filename = f"{file_name}_{current_time}.{ext}"

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    output_dir = os.path.join(base_dir, "static")

    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, pdf_filename)

    return pdf_path


def write_pdf(markdown_text, file_name, df1=None, df2=None, df3=None):

    pdf_path = create_file_path(file_name, "pdf")

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

    def add_images(file_name, df1=None, df2=None, df3=None):

        story.append(Spacer(1, 12))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"<font size=14>Approfondimenti Visivi</font>", heading_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph("In questa sezione sono presentate alcune immagini create per supportare l'analisi e i risultati discussi nelle sezioni precedenti del report. Questi visualizzazioni offrono una comprensione più chiara della situazione del magazzino, arricchendo la narrazione complessiva.", normal_style))
        story.append(Spacer(1, 12)),  # Spazio tra il testo e l'immagine

        if file_name == "report_livelli_stock":
            story.append(Paragraph(f"<font size=12>Livelli di Stock</font>", subheading_style))
            image_path = generate_stock_chart(df1)
            story.append(Image(image_path, width=700, height=300))
            story.append(Paragraph("Figura: Quantità Disponibile e Prezzo Totale per Prodotto nel Magazzino", styles["Italic"]))
            story.append(Spacer(1, 12)),  # Spazio tra il testo e l'immagine


        elif file_name == "report_movimenti_magazzino":
            story.append(Paragraph(f"<font size=12>Movimenti di Magazzino</font>", subheading_style))
            image_path = plot_movements_over_time(df1)
            story.append(Image(image_path, width=700, height=300))
            story.append(Paragraph("Figura: Distribuzione dei Movimenti nel Tempo suddivisi per Tipologia", styles["Italic"]))
            story.append(Spacer(1, 12)),  # Spazio tra il testo e l'immagine


        elif file_name == "report_performance_fornitori":
            story.append(Paragraph(f"<font size=12>Performance dei Fornitori</font>", subheading_style))
            image_path = plot_supplier_performance(df1)
            story.append(Image(image_path, width=700, height=300))
            story.append(Paragraph("Figura: Prestazioni dei Fornitori", styles["Italic"]))
            story.append(Spacer(1, 12)),  # Spazio tra il testo e l'immagine


        else:
            story.append(Paragraph(f"<font size=12>Livelli di Stock</font>", subheading_style))
            image_path = generate_stock_chart(df1)
            story.append(Image(image_path, width=700, height=300))
            story.append(Paragraph("Figura 1: Quantità Disponibile per Prodotto nel Magazzino", styles["Italic"]))
            story.append(Spacer(1, 12)),  # Spazio tra il testo e l'immagine


            story.append(Paragraph(f"<font size=12>Movimenti di Magazzino</font>", subheading_style))
            image_path = plot_movements_over_time(df2)
            story.append(Image(image_path, width=700, height=300))
            story.append(Paragraph("Figura 2: Distribuzione dei Movimenti nel Tempo suddivisi per Tipologia", styles["Italic"]))
            story.append(Spacer(1, 12)),  # Spazio tra il testo e l'immagine


            story.append(Paragraph(f"<font size=12>Performance dei Fornitori</font>", subheading_style))
            image_path = plot_supplier_performance(df3)
            story.append(Image(image_path, width=700, height=300))
            story.append(Paragraph("Figura 3: Prestazioni dei Fornitori", styles["Italic"]))
            story.append(Spacer(1, 12)),  # Spazio tra il testo e l'immagine

    add_images(file_name, df1, df2, df3)
    doc.build(story)
    print(f"✅ PDF creato: {pdf_path}")


def generate_stock_chart(stock_data):
    # Estrai le informazioni dal DataFrame
    prodotti = stock_data['Nome Prodotto']
    quantità_disponibili = stock_data["Quantità"]
    prezzo_totale = stock_data["Prezzo Totale (€)"]

    # Creazione della figura con 2 sottotrame (side by side)
    fig, ax = plt.subplots(1, 2, figsize=(18, 6))

    # Grafico per la quantità disponibile per prodotto
    ax[0].bar(prodotti, quantità_disponibili, color='skyblue')
    ax[0].set_title('Quantità Disponibile per Prodotto nel Magazzino')
    ax[0].set_ylabel('Quantità Disponibile')
    ax[0].tick_params(axis='x', rotation=45)
    ax[0].grid(axis='y', linestyle='--', alpha=0.7)

    # Grafico per la distribuzione del prezzo totale per prodotto
    ax[1].bar(prodotti, prezzo_totale, color='lightgreen')
    ax[1].set_title('Distribuzione del Prezzo Totale per Prodotto')
    ax[1].set_ylabel('Prezzo Totale (€)')
    ax[1].tick_params(axis='x', rotation=45)
    ax[1].grid(axis='y', linestyle='--', alpha=0.7)

    # Ottimizzazione del layout
    plt.tight_layout()

    # Mostra i grafici
    plt.show()

    # Salva l'immagine su file
    filename = "stock_magazzino"
    file_path = create_file_path(filename, "png")
    fig.savefig(file_path)
    plt.close()

    return file_path


def plot_movements_over_time(df):

    print(df)
    df["Data"] = pd.to_datetime(df["Data"])
    df.set_index('Data', inplace=True)

    # Mappatura delle etichette per chiarezza
    df["Tipo Movimento"] = df["Tipo Movimento"].replace({
        "🟢 Entrata": "Entrata",
        "🔴 Uscita": "Uscita"
    })

    # Dizionario colori: verde per "Entrata", rosso per "Uscita"
    colori = {"Entrata": "green", "Uscita": "red"}

    df_grouped = df.groupby(["Data", "Tipo Movimento"]).size().unstack(fill_value=0)

    print(df_grouped)

    # Creazione del grafico
    plt.figure(figsize=(10, 6))
    for movimento in df_grouped.columns:
        plt.plot(df_grouped.index, df_grouped[movimento], marker='o', label=movimento, color=colori[movimento])

    # Personalizzazione del grafico
    plt.title('Distribuzione dei Movimenti nel Tempo (Entrata vs Uscita)')
    plt.ylabel("Numero di Movimenti")

    plt.legend(title="Tipo Movimento")
    plt.grid(True)

    # Mostrare il grafico
    plt.show()

    # Salva l'immagine su file
    filename = "movimenti_magazzino"
    file_path = create_file_path(filename, "png")
    plt.savefig(file_path)
    plt.close()

    return file_path


def plot_supplier_performance(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    print(df)
    # Grafico a barre per Quantità e Prezzo Totale
    ax = axes[0]
    bar1 = ax.bar(df['Fornitore'], df['Quantità'], width=0.4, color='b', label='Quantità', align='center')
    bar2 = ax.bar(df['Fornitore'], df['Prezzo Totale'], width=0.4, color='g', label='Prezzo Totale', align='edge')

    # Manually set the legend
    ax.legend([bar1, bar2], ['Quantità', 'Prezzo Totale'], loc='best')
    
    ax.set_title('Quantità e Prezzo Totale per Fornitore')
    ax.set_ylabel('Valore')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_xticks(range(len(df['Fornitore'])))  # Imposta i tick corretti
    ax.set_xticklabels(df['Fornitore'], rotation=45, ha='right')  # Assegna le etichette
    
    # Grafico a linee per Tempo di Consegna e Ritardo Medio
    ax2 = axes[1]
    df.plot(x='Fornitore', y=['Tempo di Consegna', 'Ritardo di Consegna'], kind='line', ax=ax2, marker='o')
    ax2.set_title('Tempi di Consegna e Ritardo Medio per Fornitore')
    ax2.set_ylabel('Giorni')
    ax2.legend(loc='best')  # Ensure the legend is placed correctly
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    ax2.set_xticks(range(len(df['Fornitore'])))  # Imposta i tick corretti
    ax2.set_xticklabels(df['Fornitore'], rotation=45, ha='right')  # Assegna le etichette

    plt.tight_layout()
    plt.show()

    # Salva l'immagine su file
    filename = "performance_fornitori"
    file_path = create_file_path(filename, "png")
    plt.savefig(file_path)
    plt.close()

    return file_path