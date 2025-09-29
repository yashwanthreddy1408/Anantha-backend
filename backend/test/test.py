import os
import shutil

# Path to your main folder (contains subfolders)
main_dir ="argo_data/"

# Path where you want all meta.nc files collected
output_dir = "meta_files/"
os.makedirs(output_dir, exist_ok=True)

# Walk through all subfolders
for root, dirs, files in os.walk(main_dir):
    for file in files:
        if "meta.nc" in file:
            src = os.path.join(root, file)
            # Rename file using parent folder name to avoid overwriting
            parent_folder = os.path.basename(root)
            dst = os.path.join(output_dir, f"{parent_folder}_meta.nc")
            
            shutil.copy2(src, dst)  # copy file with metadata
            print(f"Copied {src} -> {dst}")

print("✅ All meta.nc files collected successfully.")
