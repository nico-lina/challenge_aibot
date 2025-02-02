import pandas as pd
import psycopg2 as psql

# from config import config

def connect(db):
    """ Connect to the PostgreSQL database server """
    conn = None
    try:
        # read connection parameters
       
        # params = config(section=db)
        params = {'host': 'host.docker.internal', 'database': 'test', 'user': 'odoo', 'password': 'gattaccio', 'port': '5433'}

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