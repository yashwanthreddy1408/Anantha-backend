import xarray as xr

DS = xr.open_dataset("./meta_files/4903877_meta.nc")

print(DS.keys())

print(DS['LAUNCH_LONGITUDE'].values)

print(DS.attrs)