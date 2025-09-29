import xarray as xr
import numpy as np
import pandas as pd

DS = xr.open_dataset("./5907082_data/5907082_prof.nc")

print(DS.keys(), end='\n\n\n')  

# this data consists of 
# N_PROF = 72 (no.of cycles - in each cycle data is transmitted)
# N_PARAM = 3 (pres, temp, sal)
# N_LEVELS = 104 (each progile has 104 levels depth)


print(DS['LATITUDE'].values, end = '\n\n\n')
print(DS['LONGITUDE'].values, end = '\n\n\n')
print(DS['JULD'].values, end='\n\n\n')
print(DS['PRES'].values, end='\n\n\n')
print(DS['PRES_ADJUSTED'].values, end='\n\n\n')
print(DS['PRES_QC'].values, end='\n\n\n')
print(DS['PRES_ADJUSTED_QC'].values, end='\n\n\n')
print(DS['TEMP'].values, end='\n\n\n')
print(DS['TEMP_ADJUSTED'].values, end='\n\n\n')
print(DS['TEMP_QC'].values, end='\n\n\n')
print(DS['TEMP_ADJUSTED_QC'].values, end='\n\n\n')
print(DS['PSAL'].values, end='\n\n\n')
print(DS['PSAL_ADJUSTED'].values, end='\n\n\n')
print(DS['PSAL_QC'].values, end='\n\n\n')
print(DS['PSAL_ADJUSTED_QC'].values, end='\n\n\n')



lat = DS['LATITUDE'].values
lon = DS['LONGITUDE'].values
dates = DS['JULD'].values

N_PROF = DS.sizes['N_PROF']
N_LEVELS = DS.sizes['N_LEVELS']

print("no.of profiles : ", N_PROF, end='\n\n\n')
print('no.of levels: ', N_LEVELS, end = '\n\n\n')

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
            temp[level], temp_adjusted[level], temp_qc[level] ,temp_adjusted_qc[level],
            psal[level], psal_adjusted[level], psal_qc[level] , psal_adjusted_qc[level]
        ])


df = pd.DataFrame(rows, columns=[
    "Profile", "Date", "Latitude", "Longitude",
    "Pres_raw(dbar)", "Pres_adj(dbar)", "Pres_raw_qc", "Pres_adj_qc",
    "Temp_raw(C)", "Temp_adj(C)", "Temp_raw_qc", "Temp_adj_qc",
    "Psal_raw(psu)", "Psal_adj(psu)", "Psal_raw_qc", "Psal_adj_qc",
])


df.to_csv('float_5907082.csv', index=False)
print('csvvvvv...')