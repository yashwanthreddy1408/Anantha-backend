import os
import requests
from bs4 import BeautifulSoup
import xarray as xr
import pandas as pd
import numpy as np

from load_csv_to_postgres import load_csv_to_postgres_db

base_url = "https://data-argo.ifremer.fr/dac/incois/"
download_dir = "argo_data"
os.makedirs(download_dir, exist_ok=True)

# Step 1: Get all float directories
resp = requests.get(base_url)
if resp.status_code != 200:
    raise Exception(f"Cannot access {base_url}")

soup = BeautifulSoup(resp.text, "html.parser")
float_dirs = [
    a['href'].strip("/")
    for a in soup.find_all('a')
    if a['href'].endswith("/") and a['href'][0].isdigit()
]

# ✅ Start from first float (1900121 onwards)
float_dirs = [f for f in float_dirs if int(f) >= 1900121]

print(f"Found {len(float_dirs)} float directories from 1900121 onwards")

def convert_prof_to_csv(nc_path, csv_path):
    """Convert prof.nc / Sprof.nc to a clean CSV with selected variables."""
    try:
        DS = xr.open_dataset(nc_path)

        lat = DS['LATITUDE'].values
        lon = DS['LONGITUDE'].values
        dates = DS['JULD'].values

        N_PROF = DS.sizes['N_PROF']
        N_LEVELS = DS.sizes['N_LEVELS']

        rows = []

        for i in range(N_PROF):
            pres = DS['PRES'].values[i]
            pres_adjusted = DS['PRES_ADJUSTED'].values[i]
            pres_qc = DS['PRES_QC'].values[i].astype(str)
            pres_adjusted_qc = DS['PRES_ADJUSTED_QC'].values[i].astype(str)

            temp = DS['TEMP'].values[i]
            temp_adjusted = DS['TEMP_ADJUSTED'].values[i]
            temp_qc = DS['TEMP_QC'].values[i].astype(str)
            temp_adjusted_qc = DS['TEMP_ADJUSTED_QC'].values[i].astype(str)

            psal = DS['PSAL'].values[i]
            psal_adjusted = DS['PSAL_ADJUSTED'].values[i]
            psal_qc = DS['PSAL_QC'].values[i].astype(str)
            psal_adjusted_qc = DS['PSAL_ADJUSTED_QC'].values[i].astype(str)

            for level in range(N_LEVELS):
                rows.append([
                    i+1, dates[i], lat[i], lon[i],
                    pres[level], pres_adjusted[level], pres_qc[level], pres_adjusted_qc[level],
                    temp[level], temp_adjusted[level], temp_qc[level], temp_adjusted_qc[level],
                    psal[level], psal_adjusted[level], psal_qc[level], psal_adjusted_qc[level]
                ])

        df = pd.DataFrame(rows, columns=[
            "Profile", "Date", "Latitude", "Longitude",
            "Pres_raw(dbar)", "Pres_adj(dbar)", "Pres_raw_qc", "Pres_adj_qc",
            "Temp_raw(C)", "Temp_adj(C)", "Temp_raw_qc", "Temp_adj_qc",
            "Psal_raw(psu)", "Psal_adj(psu)", "Psal_raw_qc", "Psal_adj_qc",
        ])

        df.to_csv(csv_path, index=False)
        print(f"✅ Converted {os.path.basename(nc_path)} → {os.path.basename(csv_path)} (rows: {len(df)})")

        print("Starting to add csv data to postgres db")

        load_csv_to_postgres_db(csv_path, )



    except Exception as e:
        print(f"❌ Could not convert {nc_path}: {e}")


# Step 2: Loop over each float directory
for float_dir in float_dirs:
    float_url = base_url + float_dir + "/"
    resp = requests.get(float_url)
    if resp.status_code != 200:
        print(f"Could not access {float_url}")
        continue

    soup = BeautifulSoup(resp.text, "html.parser")
    files = [a["href"] for a in soup.find_all("a") if a["href"].endswith(".nc")]

    # Create a folder for this float ID
    float_folder = os.path.join(download_dir, float_dir)
    os.makedirs(float_folder, exist_ok=True)

    # Step 3: Download only meta.nc and prof.nc (includes Sprof.nc)
    for file_name in files:
        if "meta.nc" in file_name.lower() or "prof.nc" in file_name.lower():
            local_path = os.path.join(float_folder, file_name)

            if not os.path.exists(local_path):  # avoid re-downloading
                r = requests.get(float_url + file_name)
                with open(local_path, "wb") as f:
                    f.write(r.content)
                print(f"⬇️  Downloaded {float_dir}/{file_name}")
            else:
                print(f"Already exists: {float_dir}/{file_name}")

            # If it's prof or Sprof, convert to CSV
            if "prof.nc" in file_name.lower():
                csv_name = file_name.replace(".nc", ".csv")
                csv_path = os.path.join(float_folder, csv_name)
                if not os.path.exists(csv_path):  # skip if already converted
                    convert_prof_to_csv(local_path, csv_path)