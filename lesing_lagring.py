import geopandas as gpd
import pandas as pd
import numpy as np


def les_geopandas(sti, **qwargs):
    
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


def skriv_geopandas(gdf, sti, **qwargs):
    "kopier inn"


def samle_filer(filer: list, **qwargs) -> gpd.GeoDataFrame:
    return pd.concat((les_geopandas(fil, **qwargs) for fil in filer), axis=0, ignore_index=True)


def eksisterer(sti):
    try:
        from dapla import details
        details(sti)
        return True
    except FileNotFoundError:
        return False
    except ModuleNotFoundError:
        from os.path import exists
        return exists(sti)
    
    
def lag_mappe(sti):
    if not eksisterer(sti):
        from os import makedirs
        makedirs(sti)
        
        
        
def read_invalid(sti, layer=None, **qwargs):
    """ Hvis fx en punktgeometri er kodet som LineString, klarer ikke geopandas å lese den. 
    Leser da 1000 rader av gangen, gjentar for problemradene fram til suksess. """
    
    import pyogrio
    
    rader = pyogrio.read_info(sti, layer)["features"]
    crs = pyogrio.read_info(sti, layer)["crs"]
    
    data = pd.DataFrame()
    mangler = []
    n = 0
    for i in np.arange(rader, step=1000):
        try:
            df = gpd.read_file(sti, layer=layer, engine="pyogrio", 
                                      skip_features=i, 
                                      max_features=1000, **qwargs)
            
            data = gpd.GeoDataFrame(pd.concat([data, df], axis=0, ignore_index=True), geometry="geometry", crs=crs)

            del df
            
        except Exception as e:
            mangler.append(i)
    
    print(mangler)
    print("len", len(mangler))
    
    mangler2 = []
    for i in mangler:
        for j in np.arange(start=i, stop=i+1000, step=50):
            try:
                df = gpd.read_file(sti, layer=layer, engine="pyogrio", 
                                        skip_features=j, 
                                        max_features=50, **qwargs)
                data = gpd.GeoDataFrame(pd.concat([data, df], axis=0, ignore_index=True), geometry="geometry", crs=crs)
                del df
            except Exception as e:
                mangler2.append(j)
    
    del mangler
    
    print(mangler2)
    print("len", len(mangler2))
    
    for i in mangler2:
        for j in np.arange(start=i, stop=i+50, step=1):
            try:
                df = gpd.read_file(sti, layer=layer, engine="pyogrio", 
                                        skip_features=j, 
                                        max_features=1, **qwargs)
                data = gpd.GeoDataFrame(pd.concat([data, df], axis=0, ignore_index=True), geometry="geometry", crs=crs)
                del df
            except Exception as e:
                n += 1
                if n<=5:
                    print(e)
                elif n==6:
                    print("Slutter å printe feilmeldinger")
                else:
                    pass

    print(f"{n} rader ble ikke lest")
        
    return data


if __name__=="__main__":
    x = read_invalid(r"C:\Users\ort\OneDrive - Statistisk sentralbyrå\data\ruteplanleggerSykkel_FGDB_20220601.gdb", layer="lenker_line",
                    columns=["startnode", "sluttnode", "trafikkretning", "sykkelforbud", "typeveg", "aadt", "fartsgrense"])

    x.to_parquet(r"C:\Users\ort\OneDrive - Statistisk sentralbyrå\data\ruteplanleggerSykkel_2022.parquet")
