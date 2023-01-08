import geopandas as gpd
import requests
import shutil
import os
from zipfile import ZipFile


def geonorge_json(metadataUuid, crs="25833", format = "FGDB 10.0"): # "GML 3.2.1"
    return {
    "orderLines": [
        {"metadataUuid": metadataUuid,
        "areas": [{"code": "0000", "type": "landsdekkende", "name": "Hele landet"}],
        "formats": [{"name": format}],
        "projections": [{"code": str(crs)}]}]
        }


def unzipp(zipfil, unzippet_fil):
    with ZipFile(zipfil, 'r') as z:
        z.extractall(unzippet_fil)


def slett(sti):
    if os.path.isfile(sti):
        os.remove(sti)
    if os.path.isdir(sti):
        shutil.rmtree(sti)
        
  
def hent_fra_geonorge(metadataUuid, sti, **qwargs):

    geonorge = "https://nedlasting.geonorge.no/api/order"
    
    zipfil = sti+".zip"
  
    js = geonorge_json(metadataUuid, **qwargs)
    
    p = requests.post(geonorge, json=js)
    p = p.json()
    
    download_url = p["files"][0]["downloadUrl"]
    filnavn = p["files"][0]["name"]

    r = requests.get(download_url)
    innhold = r.content

    with open(zipfil, 'wb') as fil:
      fil.write(innhold)
  
    unzipp(zipfil, sti)
  
    # til parquet?
    gdbfil = f"{sti}/{filnavn.strip('.zip')}.gdb"
    parquetfil = sti + ".parquet"
    gpd.read_file(gdbfil).to_parquet(parquetfil)
    
    slett(zipfil)
    slett(gdbfil)
    slett(sti)
    


if __name__=="__main__":
    
    n5000_uuid = "c777d53d-8916-4d9d-bae4-6d5140e0c569"
    sti = f"C:/Users/ort/OneDrive - Statistisk sentralbyrå/data/n5000"
    
    hent_fra_geonorge(n5000_uuid, sti)
    
    print(gpd.read_parquet(sti+".parquet"))

