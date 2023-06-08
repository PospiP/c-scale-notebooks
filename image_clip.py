"""
This function clipped all images in specified folder according to the geojson file and save output to specified folder
"""
import os
import re
import pyproj
import numpy as np
import json
import os
import fiona
import rasterio
from rasterio.mask import mask

def clipper(image_path, geojson, new_folder, L2A = "no", B09 = "no", whole = "no"):
    file_list = os.listdir(image_path)
    file_list.sort()
    
    if ".ipynb_checkpoints" in file_list:
        indx = file_list.index(".ipynb_checkpoints")
        del file_list[indx]

    # use fiona to open our map ROI GeoJSON
    with fiona.open(geojson) as f:
        aoi = [feature["geometry"] for feature in f]
        
    if B09 == "no":    
        # Load every image from the list
        k = 0
        for image in file_list:
            with rasterio.open(image_path + image) as img:
                clipped, transform = mask(img, aoi, crop=True)
    
            meta = img.meta.copy()
    
            meta.update({"driver": "GTiff", "transform": transform,"height":clipped.shape[1],"width":clipped.shape[2]})
    
            # Save clipped images in the file
            if L2A == "yes":
                inilist = [i.start() for i in re.finditer("_",file_list[k])]
                new_fold = new_folder + file_list[k][inilist[1]+1:inilist[2]] + '.tif'
            elif whole == "no":
                new_fold = new_folder + file_list[k][file_list[k].rfind('_')+1:file_list[k].rfind('.')] + '.tif'
            else:
                new_fold = new_folder + file_list[k]
            
            with rasterio.open(new_fold, 'w', **meta) as dst:
                dst.write(clipped)
                
            k += 1
    else:
        name09 = ([s for s in file_list if "B09" in s])
        
        with rasterio.open(image_path + name09[0]) as img:
                clipped, transform = mask(img, aoi, crop=True)
    
        meta = img.meta.copy()
    
        meta.update({"driver": "GTiff", "transform": transform,"height":clipped.shape[1],"width":clipped.shape[2]})
        
        inilist = [i.start() for i in re.finditer("_",name09[0])]
        new_fold = new_folder + name09[0][inilist[1]+1:inilist[2]] + '.tif'
        
        with rasterio.open(new_fold, 'w', **meta) as dst:
                dst.write(clipped)
        
    print("All clipped images are saved in {} folder!".format(new_folder))

