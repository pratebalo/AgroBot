import json
from datetime import datetime, date

from bot_base.logger_config import logger
import pandas as pd
import numpy as np

from decouple import config
from sqlalchemy import create_engine, text

HOST = config("HOST")
USER_DB = config("DB_USER")
DATABASE = config("DB_NAME")
PASSWORD_DB = config("DB_PASS")
engine = create_engine(f'postgresql://{USER_DB}:{PASSWORD_DB}@{HOST}:5433/{DATABASE}')
connection = engine.connect()


def select(table):
    query = text(f"SELECT * FROM {table}")
    result = pd.read_sql(query, engine).sort_values(by="id", ignore_index=True)
    return result


def select_where(table, clauses, values):
    query = text(f"""SELECT * FROM {table} 
    WHERE {" AND ".join([f"{field} = {format_value(value)}" for field, value in zip(clauses, values)])} """)
    result = pd.read_sql(query, engine).sort_values(by="id", ignore_index=True)
    return result


def delete(table, idx):
    query = text(f"""DELETE FROM {table}
            WHERE id = {idx}
            RETURNING *;""")
    result = pd.read_sql(query, connection)
    connection.commit()

    return result


def update_fields_table(table: str, idx: int, **fields):
    query = text(f"""set DateStyle='ISO, DMY';
        UPDATE {table}
        SET {", ".join([f"{field} = {format_value(value)}" for field, value in fields.items()])}
        WHERE id = {idx}
        RETURNING *;""")
    return connect(query)


def insert_into_table(table: str, **fields):
    field_names = fields.keys()
    field_values = fields.values()
    query = text(f"""set DateStyle='ISO, DMY';
    INSERT INTO {table}
    ({", ".join(field_names)})
     VALUES ({", ".join(list(map(format_value, field_values)))})
    RETURNING *;""")
    return connect(query)


def format_value(val):
    match val:
        case str() | date():
            return f"'{val}'"
        case int() | float() | np.int64():
            return str(val)
        case bool():
            return 'TRUE' if val else 'FALSE'
        case None:
            return 'NULL'
        case list():
            if len(val) == 0:
                return f"ARRAY[]::TEXT[]"
            else:
                return f"ARRAY{val}"
        case dict():
            return f"'{json.dumps(val)}'::jsonb"
        case _:
            raise ValueError(f"Tipo de dato no soportado: {type(val)}")


def connect(query):
    try:
        result = connection.execute(query)
        if result.returns_rows:
            if result.rowcount == 1:
                df = pd.Series(result.fetchall()[0], index=result.keys())
            else:
                df = pd.DataFrame(result.fetchall(), columns=list(result.keys()))
        else:
            df = None
    except Exception as e:
        connection.rollback()
        logger.error(f"Error: {e}")
        return None
    else:
        connection.commit()
        return df
