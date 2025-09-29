from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text
import pandas as pd

# Load .env
load_dotenv()

# Get DB_URL from environment
DB_URL = os.getenv("DB_URL")

# Create SQLAlchemy engine
engine = create_engine(DB_URL, connect_args={"connect_timeout": 30})

def retrieve_data_from_postgres(sql_query: str) -> pd.DataFrame:
    """Execute a SQL query on Cloud SQL and return a pandas DataFrame."""
    try:
        # Clean the SQL query
        sql_query = sql_query.strip()
        if not sql_query:
            print("Error: Empty SQL query")
            return pd.DataFrame()
        
        print(f"Executing SQL: {sql_query[:200]}...")  # Log first 200 chars
        
        with engine.connect() as conn:
            # Use text() to properly handle the SQL query
            df = pd.read_sql(text(sql_query), conn)
        
        print(f"Retrieved {len(df)} rows with columns: {df.columns.tolist()}")
        return df
        
    except Exception as e:
        print(f"Error retrieving data from postgres: {e}")
        print(f"Failed SQL query: {sql_query}")
        return pd.DataFrame()