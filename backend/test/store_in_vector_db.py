import xarray as xr

DS = xr.open_dataset("./meta_files/1900121_meta.nc")

print(DS.keys())

for i in DS.keys():
    print(i," : ",DS[i].values)