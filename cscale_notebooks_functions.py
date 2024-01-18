import zipfile
import pandas as pd
import geopandas as gpd
import numpy as np
import shapefile
import io
import os
import geojson
import rasterio
from rasterio.coords import BoundingBox
from shapely.geometry import shape
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, MultiPolygon
import matplotlib.pyplot as plt
from pathlib import Path
from rasterio.enums import Resampling
from rasterio.plot import adjust_band

def get_cloud_cover_ts(gdf: gpd.geodataframe.GeoDataFrame) -> pd.core.series.Series:
    ts = None
    try:
        gdf["datetime"] = pd.to_datetime(gdf["datetime"])
        _ts = gdf.set_index("datetime").sort_index()["eo:cloud_cover"]
    except KeyError:
        print("eo:cloud_cover not available")
    else:
        ts = _ts 
    return ts

def geojson_map_eu(string_path):
    # Open geojson file with GPS coordinates
    with open(string_path) as f:
        gj = geojson.load(f)
    coor = gj['features'][0]['geometry']['coordinates']
    
    # Example list of lists with tuples representing coordinates
    multipolygon_coordinates = coor

    # Convert the coordinates to MultiPolygon geometry
    multipolygon_geometry = MultiPolygon([Polygon(coords) for sublist in multipolygon_coordinates for coords in sublist])

    # Create a GeoDataFrame with the MultiPolygon geometry
    data = {'ID': [1], 'geometry': [multipolygon_geometry]}
    gdf = gpd.GeoDataFrame(data)

    # Print the GeoDataFrame
    return gdf

def read_gdf(file_path):
    # Open geojson file with GPS coordinates
    with open(file_path) as f:
        gj = geojson.load(f)

    # Load coordinates from geojson file
    coor = gj['features'][0]['geometry']['coordinates']

    x_list = np.zeros(len(coor[0]))
    y_list = np.zeros(len(coor[0]))

    for i in range(0, len(coor[0])):
        x_list[i] = coor[0][i][0]
        y_list[i] = coor[0][i][1]

    bbox = [x_list.min(),y_list.min(),x_list.max(),y_list.max()]
    return bbox

def pol_to_np(pol):
    """
    Receives list of coordinates: [[x1,y1],[x2,y2],...,[xN,yN]]
    """
    return np.array([list(l) for l in pol])

def pol_to_bounding_box(pol):
    """
    Receives list of coordinates: [[x1,y1],[x2,y2],...,[xN,yN]]
    """
    arr = pol_to_np(pol)
    return BoundingBox(np.min(arr[:,0]),
                       np.min(arr[:,1]),
                       np.max(arr[:,0]),
                       np.max(arr[:,1]))

def reverse_coordinates(pol):
    """
    Reverse the coordinates in pol
    Receives list of coordinates: [[x1,y1],[x2,y2],...,[xN,yN]]
    Returns [[y1,x1],[y2,x2],...,[yN,xN]]
    """
    return [list(f[-1::-1]) for f in pol]

def to_index(wind_):
    """
    Generates a list of index (row,col): [[row1,col1],[row2,col2],[row3,col3],[row4,col4],[row1,col1]]
    """
    return [[wind_.row_off,wind_.col_off],
            [wind_.row_off,wind_.col_off+wind_.width],
            [wind_.row_off+wind_.height,wind_.col_off+wind_.width],
            [wind_.row_off+wind_.height,wind_.col_off],
            [wind_.row_off,wind_.col_off]]

def generate_polygon(bbox):
    """
    Generates a list of coordinates: [[x1,y1],[x2,y2],[x3,y3],[x4,y4],[x1,y1]]
    """
    return [[bbox[0],bbox[1]],
             [bbox[2],bbox[1]],
             [bbox[2],bbox[3]],
             [bbox[0],bbox[3]],
             [bbox[0],bbox[1]]]

def pol_to_np(pol):
    """
    Receives list of coordinates: [[x1,y1],[x2,y2],...,[xN,yN]]
    """
    return np.array([list(l) for l in pol])

def pol_to_bounding_box(pol):
    """
    Receives list of coordinates: [[x1,y1],[x2,y2],...,[xN,yN]]
    """
    arr = pol_to_np(pol)
    return BoundingBox(np.min(arr[:,0]),
                       np.min(arr[:,1]),
                       np.max(arr[:,0]),
                       np.max(arr[:,1]))

def resampling(folder, file_template, file_resize, upscale_factor):
    upscale_factor = upscale_factor
    
    with rasterio.open(folder + file_template) as dataset:
        template = dataset.read(out_shape=(dataset.count,
                                       int(dataset.height),
                                       int(dataset.width)
                                      ))
    
    with rasterio.open(folder + file_resize) as dataset:        
        # resample data to target shape
        data = dataset.read(out_shape=(dataset.count,
                                       int(dataset.height * upscale_factor),
                                       int(dataset.width * upscale_factor)),
                                       resampling=Resampling.cubic)
        
    # scale image transform
    transform = dataset.transform * dataset.transform.scale(
        (dataset.width / data.shape[-1]),
        (dataset.height / data.shape[-2])
    )
    
    resample = data.reshape(data.shape[0]*(data.shape[1], data.shape[0]*data.shape[2]))
    
    a = template.shape[1] - resample.shape[0]
    b = template.shape[2] - resample.shape[1]
    
    resized = np.delete(resample,range(0,abs(a)),0)
    resized = np.delete(resized,range(0,abs(b)),1)
    
    new_array = np.asarray(resized).reshape(1,resized.shape[0], resized.shape[1])
    
    meta = dataset.meta.copy()
    
    meta.update({ "transform": transform, "height":new_array.shape[1],"width":new_array.shape[2]})
    
    index = file_resize.rfind(".")
    file_pre  = file_resize[0:index]
    file_suf = file_resize[index:]
    
    with rasterio.open(folder + file_pre + "_res" + file_suf, 'w+', **meta) as dst:
            dst.write(new_array)
    
    return new_array

def load_sentinel_image(img_folder, bands):
    image = {}
    path = Path(img_folder)
    for band in bands:
        file = img_folder + band + ".tif" 
        #print(f'Opening file {file}')
        ds = rasterio.open(file)
        image.update({band: ds.read(1)})

    return image

def display_rgb(img, b_r, b_g, b_b, alpha=1., figsize=(10, 10)):
    rgb = np.stack([img[b_r], img[b_g], img[b_b]], axis=-1)
    rgb = rgb/rgb.max() * alpha
    plt.figure(figsize=figsize)
    plt.imshow(rgb)
    plt.axis("off")
    
def image_rgb(img, b_r, b_g, b_b, alpha=1.):
    rgb = np.stack([img[b_r], img[b_g], img[b_b]], axis=-1)
    rgb = adjust_band(rgb)
    rgb = rgb/rgb.max() * alpha
    return rgb

def normalized_difference(img, b1, b2, eps=0.0001):
    band1 = np.where((img[b1]==0) & (img[b2]==0), np.nan, img[b1])
    band2 = np.where((img[b1]==0) & (img[b2]==0), np.nan, img[b2])
    
    return (band1 - band2) / (band1 + band2)

def plot_masked_rgb(red, green, blue, mask, color_mask=(1, 0, 0), transparency=0.5, brightness=2):
    
    # to improve our visualization, we will increase the brightness of our values
    red = red / red.max() * brightness
    green = green / green.max() * brightness
    blue = blue / blue.max() * brightness
    
    red = np.where(mask==True, red*transparency+color_mask[0]*(1-transparency), red)
    green = np.where(mask==True, green*transparency+color_mask[1]*(1-transparency), green)
    blue = np.where(mask==True, blue*transparency+color_mask[2]*(1-transparency), blue)
    
    rgb = np.stack([red, green, blue], axis=2)
    
    return rgb