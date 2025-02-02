from cat.mad_hatter.decorators import tool, hook
from .utili import connect
import pandas as pd

@tool(return_direct=True)
def get_the_warehouse_status(tool_input, cat):
    """Replies to "what is the warehouse status", and similar questions. Input is always None.."""
    print("AAAAAAA")
    
    db = connect("gattaccio")
    query = """SELECT
        --pp.id AS product_id,
        pt.name->>'it_IT' AS product_name,
        pp.default_code AS product_variant,
        --sq.location_id,
        sl.name as warehouse_name,
        SUM(sq.quantity) as quantity,
        SUM(sq.reserved_quantity) as reserved_quantity,
        (SUM(sq.quantity) - SUM(sq.reserved_quantity)) AS available_quantity
    FROM
        stock_quant sq
    JOIN
        product_product pp ON pp.id = sq.product_id
    JOIN
        product_template pt ON pp.product_tmpl_id = pt.id
    JOIN 
        stock_location sl ON sl.id = sq.location_id
    WHERE
        sq.quantity > 0  -- Per mostrare solo i prodotti con quantità disponibile
    GROUP BY
        pp.id, pt.name, pp.default_code, sq.location_id, sl.name
    ORDER BY
        product_name;
    """
    df = pd.read_sql_query(query, db)
    db.close()
    mark = df.to_markdown(index=False)
    
    output = cat.llm(
        f"""Riscrivi, in modo chiaro per l'utente, applicando una formattazione che renda tutto 
        molto leggibile e in formato discorsivo, i dati contenuti in questa tabella:
        
        {mark}
        """, stream=True
    )
    output = output.replace("**", "")
    

    return output