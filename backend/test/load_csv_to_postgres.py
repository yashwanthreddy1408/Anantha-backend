from dotenv import load_dotenv 
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL=os.getenv("DB_URL")

def load_csv_to_postgres_db(csv_path):
    # ---- CONFIG ----
    CSV_PATH = csv_path                 # path to your CSV
    BATCH_SIZE = 5000                          # tune for speed

    # ---- Load CSV ----
    df = pd.read_csv(CSV_PATH, na_values=['nan'])

    # Expected columns (case-sensitive): adjust if yours differ
    # Profile, Date, Latitude, Longitude,
    # Pres_raw(dbar), Pres_adj(dbar), Pres_raw_qc, Pres_adj_qc,
    # Temp_raw(C), Temp_adj(C), Temp_raw_qc, Temp_adj_qc,
    # Psal_raw(psu), Psal_adj(psu), Psal_raw_qc, Psal_adj_qc

    # Fallbacks: adj → raw
    df["pres"] = df["Pres_adj(dbar)"].fillna(df["Pres_raw(dbar)"])
    df["temp"] = df["Temp_adj(C)"].fillna(df["Temp_raw(C)"])
    df["psal"] = df["Psal_adj(psu)"].fillna(df["Psal_raw(psu)"])

    df["qc_pres"] = df["Pres_adj_qc"].fillna(df["Pres_raw_qc"])
    df["qc_temp"] = df["Temp_adj_qc"].fillna(df["Temp_raw_qc"])
    df["qc_psal"] = df["Psal_adj_qc"].fillna(df["Psal_raw_qc"])

    # Replace remaining NaNs with None (so Postgres stores NULL)
    df = df.replace({np.nan: None})

    # Prepare rows (minimal columns in the final table)
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "float_id": r["Float_ID"] if r["Float_ID"] is not None else None,
            "profile": int(r["Profile"]) if r["Profile"] is not None else None,
            "obs_time": r["Date"],  # Postgres will parse 'YYYY-MM-DD HH:MM:SS'
            "lon": float(r["Longitude"]) if r["Longitude"] is not None else None,
            "lat": float(r["Latitude"])  if r["Latitude"]  is not None else None,
            "pres": None if r["pres"] is None else float(r["pres"]),
            "temp": None if r["temp"] is None else float(r["temp"]),
            "psal": None if r["psal"] is None else float(r["psal"]),
            "qc_pres": None if r["qc_pres"] is None else int(r["qc_pres"]),
            "qc_temp": None if r["qc_temp"] is None else int(r["qc_temp"]),
            "qc_psal": None if r["qc_psal"] is None else int(r["qc_psal"]),
        })

    # Insert
    engine = create_engine(DB_URL, future=True)

    insert_sql = text("""
    INSERT INTO profileData
    (float_id, profile, obs_time, geom, pres, temp, psal, qc_pres, qc_temp, qc_psal)
    VALUES
    (:float_id, :profile, :obs_time,
    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
    :pres, :temp, :psal, :qc_pres, :qc_temp, :qc_psal)
    """)

    with engine.begin() as conn:
        # batch insert to reduce round trips
        for i in range(0, len(rows), BATCH_SIZE):
            conn.execute(insert_sql, rows[i:i+BATCH_SIZE])

    print("✅ Loaded CSV into PostGIS with fallbacks and NULLs.")
