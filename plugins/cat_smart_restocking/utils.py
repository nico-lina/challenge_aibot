import pandas as pd
import odoorpc
import psycopg2 as psql
from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import datetime, timedelta
from rapidfuzz import process, fuzz


def connect(db):
    """ Connette al database PostgreSQL """
    try:
        params = {
            'host': 'host.docker.internal',
            'database': 'AI_Battle',
            'user': 'odoo',
            'password': 'AIBattle',
            'port': '5433'
        }
        return psql.connect(**params)
    except (Exception, psql.DatabaseError) as error:
        print(f"Errore di connessione al database: {error}")
        return None

def get_odoo_connection():
    """ Connette a Odoo """
    odoo = odoorpc.ODOO('host.docker.internal', port=8069)
    odoo.login('AI_Battle', 'admin', 'admin')
    return odoo

def get_product_by_name(product_name):

    odoo = get_odoo_connection()
    Product = odoo.env['product.product']
    
    products = Product.search_read([], ['name'])
    
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
        print("MATCHED PRODUCT: ", matched_product)
        return {
            "id": matched_product["id"],
            "name": matched_product["name"]
        }
    
    # Se nessun match supera 90, filtra quelli con score > 50
    valid_matches = [match[0] for match in matches if match[1] > 45]

    if not valid_matches:
        return None
    
    # Troviamo i prodotti corrispondenti nel database
    matched_products = [prod for prod in products if prod['name'] in valid_matches]
    
    return {
        "multiple_matches": [
            {"id": prod["id"], "name": prod["name"]}
            for prod in matched_products
        ]
    }

def predict_future_demand(id, months: int):
    """Predice la domanda futura per prodotto su base mensile basandosi sui dati storici degli ordini."""
    odoo = get_odoo_connection()
    PurchaseLine = odoo.env['purchase.order.line']
    
    product_id = get_product_by_name(id)

    quantity = PurchaseLine.search_read([('product_id', '=', product_id['id'])], ['date_planned', 'name', 'product_qty'])

    df = pd.DataFrame(quantity)
    df["order_date"] = pd.to_datetime(df["date_planned"])
    
    # Aggregazione della quantità totale per prodotto e mese
    df["year_month"] = df["order_date"].dt.to_period("M")
    df = df.groupby(['name', 'year_month'])['product_qty'].sum().reset_index()
    
    # Convertire il periodo in un valore numerico per la regressione
    df["months_since_start"] = (df["year_month"].astype(str).astype("datetime64") - df["year_month"].min().to_timestamp()).dt.days // 30
    df["months_since_start"] = df["months_since_start"].astype(int)  # Ensure it's an integer type
        
    predictions = {}
    
    months = int(months)

    for product in df["name"].unique():
        product_df = df[df["name"] == product]
        
        X = product_df[["months_since_start"]]
        y = product_df["product_qty"]
        
        model = LinearRegression()
        model.fit(X, y)
        
        future_months = np.arange(product_df["months_since_start"].max() + 1, 
                                  product_df["months_since_start"].max() + months + 1).reshape(-1, 1)
        future_predictions = model.predict(future_months)
        
        predictions[product] = {str((df["year_month"].max() + i).to_timestamp().strftime('%Y-%m')): pred 
                                for i, pred in enumerate(future_predictions, 1)}
    
    return predictions


def suggest_reorder_date(name, months_ahead=3):
    """
    Suggerisce la migliore data per il riordino basandosi sulla domanda prevista,
    in modo da non scendere sotto la quantità minima.
    """
    odoo = get_odoo_connection()
    StockWarehouse = odoo.env['stock.warehouse.orderpoint']
    PurchaseLine = odoo.env['purchase.order.line']

    id = get_product_by_name(name)

    # Recupero dati di stock e ordini
    stock_data = StockWarehouse.search_read([('product_id', '=', id['id'])], ['product_id', 'product_min_qty', 'product_max_qty'])
    order_data = PurchaseLine.search_read([('product_id', '=', id['id'])], ['product_id', 'name', 'product_qty', 'create_date', 'date_planned'])

    stock_df = pd.DataFrame(stock_data)
    order_df = pd.DataFrame(order_data)

    if stock_df.empty:
        raise ValueError("Nessun dato di stock disponibile.")
    
    order_df.rename(columns={'create_date': 'date_order'}, inplace=True)
    order_df['date_order'] = pd.to_datetime(order_df['date_order'])

    for i in range(len(stock_df)):
        stock_df.at[i, 'product_id'] = stock_df.at[i, 'product_id'][0]

    for i in range(len(order_df)):
        order_df.at[i, 'product_id'] = order_df.at[i, 'product_id'][0]

    # Unire i dati di stock con gli ordini
    stock_df = stock_df.merge(order_df, on='product_id', how='left')
    
    reorder_dates = {}
    
    # Ottieni previsioni della domanda futura per i prossimi mesi
    future_demand = predict_future_demand(name, months_ahead)
    
    for _, row in stock_df.iterrows():
        product_id = row['product_id']
        product_name = row['name']
        current_stock = row['product_qty']
        min_qty = row['product_min_qty']
        
        # Se il prodotto non ha previsioni, salta
        if product_name not in future_demand:
            continue

        # Convertire la previsione mensile in un consumo giornaliero stimato
        future_demand_values = list(future_demand[product_name].values())
        avg_daily_demand = sum(future_demand_values) / (months_ahead * 30)
        
        reorder_date = datetime.today()

        # Simula il consumo futuro per determinare la data di riordino
        while current_stock > min_qty:
            current_stock -= avg_daily_demand
            reorder_date += timedelta(days=1)
        
        reorder_dates[product_name] = reorder_date.strftime('%Y-%m-%d')

    return reorder_dates
