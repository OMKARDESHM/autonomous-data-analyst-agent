# inspect_schema.py

from sqlalchemy import inspect

from config import engine

inspector = inspect(engine)

print("Tables:")

for table in inspector.get_table_names():

    print(table)

    for column in inspector.get_columns(table):

        print("   ", column["name"], column["type"])