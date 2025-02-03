import pandas as pd
import odoorpc
import psycopg2 as psql

# from config import config

def connect(db):
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # read connection parameters
       
        # params = config(section=db)
        params = {'host': 'host.docker.internal', 'database': 'health1', 'user': 'odoo', 'password': 'gattaccio', 'port': '5433'}

        # connect to the PostgreSQL server
        # print('Connecting to the PostgreSQL database...')
        conn = psql.connect(**params)

        return conn
    except (Exception, psql.DatabaseError) as error:
        print(error)
    # finally:
    #     if conn is not None:
    #         conn.close()
    #         print('Database connection closed.')

def get_warehouse():
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  # Cambia host e porta se necessario

    # Autenticazione
    db = 'health1'
    username = 'admin'
    password = 'admin'
    odoo.login(db, username, password)

    # Modelli Odoo
    Product = odoo.env['product.product']
    StockQuant = odoo.env['stock.quant']
    StockLocation = odoo.env['stock.location']
    OrderPoint = odoo.env['stock.warehouse.orderpoint']

    # Recupero prodotti con quantità disponibili a magazzino
    products = Product.search_read([], ['id', 'name'])

    # Lista per raccogliere i dati
    data = []

    for product in products:
        product_id = product['id']
        product_name = product['name']
        
        # Ottieni le quantità per il prodotto
        quants = StockQuant.search_read([('product_id', '=', product_id)], ['location_id', 'quantity', 'reserved_quantity'])
        orderpoint = OrderPoint.search_read([('product_id', '=', product_id)], ['product_min_qty'])
        min_qty = orderpoint[0]['product_min_qty'] if orderpoint else 0  # Default a 0 se non è impostata

        for quant in quants:
            location_id = quant['location_id'][0]
            
            # Ottieni il nome del magazzino dalla location
            location_data = StockLocation.browse(location_id)
            warehouse_name = location_data.display_name if location_data else "Sconosciuto"
            
            # Aggiungi i dati alla lista
            data.append({
                'Prodotto': product_name,
                # 'Magazzino': warehouse_name,
                'Quantità Disponibile': quant['quantity'],
                'Quantità Riservata': quant['reserved_quantity'],
                'Quantità Minima di Riordino': min_qty
            })

    # Creazione DataFrame
    df = pd.DataFrame(data)
    df = df[df["Quantità Disponibile"] >= 0]

    # Stampa il DataFrame
    mark = df.to_markdown(index=False)
    
    return mark


def create_product(product_name, product_qty, product_min_qty, product_description):
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)  

    db = 'health1'
    username = 'admin'
    password = 'admin'
    odoo.login(db, username, password)

    Product = odoo.env['product.product']
    StockQuant = odoo.env['stock.quant']
    StockLocation = odoo.env['stock.location']
    OrderPoint = odoo.env['stock.warehouse.orderpoint']


    new_product_id = Product.create({
        'name': product_name,
        'is_storable': True,  
        'categ_id': 1,
        'description': product_description,
    })


    location_id = StockLocation.search([('usage', '=', 'internal')], limit=1)[0]

    StockQuant.create({
        'product_id': new_product_id,
        'location_id': location_id,
        'quantity': product_qty,
    })

    OrderPoint.create({
        'product_id': new_product_id,
        'location_id': location_id,
        'product_min_qty': product_min_qty,  
        'product_max_qty': product_min_qty, 
    })
    
    odoo_url = 'http://localhost:8069/web#id={}&model=product.product&view_type=form'.format(new_product_id)
    return [True, odoo_url]