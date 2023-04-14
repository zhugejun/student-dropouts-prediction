import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


def get_data_from_cams(query):
    """Returns data pulled from CAMS by query"""

    print(">>>>>> CAMS <<<<<<")

    connection_string = """DRIVER={SQL Server};
        SERVER=gc-sql-aws;
        DATABASE=CAMS_Enterprise;
        Trusted_Connection=yes;"""
    connection_url = URL.create(
        "mssql+pyodbc", query={"odbc_connect": connection_string}
    )
    engine = create_engine(connection_url)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


if __name__ == "__main__":
    df = get_data_from_cams("select top 1 * from Student")
    print(df)
