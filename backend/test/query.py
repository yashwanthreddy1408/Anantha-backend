import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")

from sqlalchemy import create_engine, text
import pandas as pd

engine = create_engine(DB_URL)

with engine.connect() as conn:
#     result = conn.execute(text("""

#         SELECT id, float_id, profile, obs_time, pres, temp, psal
#         FROM profileData
#         ORDER BY obs_time
#         LIMIT 8;
# """))
    
    # for row in result:
    #     print(row)


    df = pd.read_sql("""
        SELECT column_name, data_type
        FROM profileData
        ;          
    """, conn)


    # conn.execute(text("DELETE FROM profileData;"))

    
print(df)



