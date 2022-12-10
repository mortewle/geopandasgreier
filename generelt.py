import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.wkt import loads

  
def read_geopandas(sti, **qwargs):
    try:
        from dapla import FileClient
        fs = FileClient.get_gcs_file_system()
        with fs.open(sti, mode='rb') as file: 
            if "parquet" in sti:
                return gpd.read_parquet(file, **qwargs)
            return gpd.read_file(file, **qwargs)
    except Exception:
        try:
            return gpd.read_parquet(sti, **qwargs)
        except Exception:
            return gpd.read_file(sti, **qwargs)


def samle_filer(filer, **qwargs):
    return pd.concat((read_geopandas(fil, **qwargs) for fil in filer), axis=0, ignore_index=True)
    
    
# konverterer til geodataframe fra geoseries, shapely-objekt, wkt, liste med shapely-objekter eller shapely-sekvenser 
# OBS: når man har shapely-objekter eller wkt, bør man sette crs. 
def til_gdf(geom, set_crs=None, **qwargs) -> gpd.GeoDataFrame:

    if isinstance(geom, str):
        from shapely.wkt import loads
        geom = loads(geom)
        gdf = gpd.GeoDataFrame({"geometry": gpd.GeoSeries(geom)}, **qwargs)
    else:
        gdf = gpd.GeoDataFrame({"geometry": gpd.GeoSeries(geom)}, **qwargs)

    if set_crs:
        gdf = gdf.set_crs(set_crs)
    
    return gdf


# fjerner tomme geometrier og NaN-geometrier
def fjern_tomme_geometrier(gdf):
    if isinstance(gdf, gpd.GeoDataFrame):
        gdf = gdf[~gdf.geometry.is_empty]
        gdf = gdf.dropna(subset = ["geometry"])
    elif isinstance(gdf, gpd.GeoSeries):
        gdf = gdf[~gdf.is_empty]
        gdf = gdf.dropna()
    else:
        raise ValueError("Input må være GeoDataFrame eller GeoSeries")
    return gdf


# samler liste med geodataframes til en lang geodataframe
def gdf_concat(gdf_liste: list, 
               crs=None, axis=0, ignore_index=True, geometry="geometry", **qwargs) -> gpd.GeoDataFrame:
    
    if crs is None:
        crs = gdf_liste[0].crs
    
    return gpd.GeoDataFrame(
        pd.concat(gdf_liste, axis=axis, ignore_index=ignore_index, **qwargs), 
        geometry=geometry, crs=crs)
    

# lager n tilfeldige punkter innenfor et gitt område (mask)
def tilfeldige_punkter(n, mask=None):
    import random
    if mask is None:
        x = np.array([random.random()*10**7 for _ in range(n*1000)])
        y = np.array([random.random()*10**8 for _ in range(n*1000)])
        punkter = til_gdf([loads(f"POINT ({x} {y})") for x, y in zip(x, y)], crs=25833)
        return punkter
    mask_kopi = mask.copy()
    mask_kopi = mask_kopi.to_crs(25833)
    out = gpd.GeoDataFrame({"geometry":[]}, geometry="geometry", crs=25833)
    while len(out) < n:
        x = np.array([random.random()*10**7 for _ in range(n*1000)])
        x = x[(x > mask_kopi.bounds.minx.iloc[0]) & (x < mask_kopi.bounds.maxx.iloc[0])]
        
        y = np.array([random.random()*10**8 for _ in range(n*1000)])
        y = y[(y > mask_kopi.bounds.miny.iloc[0]) & (y < mask_kopi.bounds.maxy.iloc[0])]
        
        punkter = til_gdf([loads(f"POINT ({x} {y})") for x, y in zip(x, y)], crs=25833)
        overlapper = punkter.clip(mask_kopi)
        out = gdf_concat([out, overlapper])
    out = out.sample(n).reset_index(drop=True).to_crs(mask.crs)
    out["idx"] = out.index
    return out