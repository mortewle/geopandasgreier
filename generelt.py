"""
Ymse funksjoner som kan brukes med geopandas.
"""
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


def samle_filer(filer: list, **qwargs) -> gpd.GeoDataFrame:
    return pd.concat((read_geopandas(fil, **qwargs) for fil in filer), axis=0, ignore_index=True)
    

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
    

#en overlay-variant som ikke finnes i geopandas
def overlay_update(gdf1: gpd.GeoDataFrame,
                   gdf2: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = gdf1.overlay(gdf2, how = "difference", keep_geom_type=True)
    out = gdf_concat([out, gdf2])
    out = out.loc[:, ~out.columns.str.contains('index|level_')]
    return(out)


# som gpd.sjoin bare at kolonner i right_gdf som også er i left_gdf fjernes (fordi det snart vil gi feilmelding i geopandas)
# og kolonner som har med index å gjøre fjernes, fordi sjoin ofte returnerer index_right som kolonnenavn, som gir feilmelding ved neste join.
def min_sjoin(left_gdf, right_gdf, dask=False, npartitions=8, **kwargs):

    #fjern index-kolonner
    left_gdf = left_gdf.loc[:, ~left_gdf.columns.str.contains('index|level_')]
    right_gdf = right_gdf.loc[:, ~right_gdf.columns.str.contains('index|level_')]

    #fjern kolonner fra gdf2 som er i gdf1
    fjernede_kolonner = []
    for kolonne in right_gdf.columns:
        if kolonne in left_gdf.columns:
            if kolonne != "geometry":
                right_gdf = right_gdf.drop(kolonne, axis=1)
                fjernede_kolonner.append(kolonne)
    if len(fjernede_kolonner) > 0:
        print(f"OBS: fjerner kolonnene {', '.join(fjernede_kolonner)} fra right_gdf fordi de finnes i left_gdf")

    joinet = left_gdf.sjoin(right_gdf, **kwargs)
        
    return joinet.loc[:, ~joinet.columns.str.contains('index|level_')]


# snapper (flytter) fra punkter til naermeste punkt/linje/polygon innen en gitt maks_distanse
# går via nearest_points for å finne det nøyaktige punktet. Med kun snap() blir det ikke riktig.
# funker med geodataframes, geoseries og shapely-objekter
def snap_til(punkter, snap_til, maks_distanse=500):

    from shapely.ops import nearest_points, snap

    snap_til_shapely = snap_til.unary_union

    if isinstance(punkter, gpd.GeoDataFrame):
        for i, punkt in enumerate(punkter.geometry):
            nearest = nearest_points(punkt, snap_til_shapely)[1] 
            snappet_punkt = snap(punkt, nearest, tolerance=maks_distanse)
            punkter.geometry.iloc[i] = snappet_punkt

    if isinstance(punkter, gpd.GeoSeries):
        for i, punkt in enumerate(punkter):
            nearest = nearest_points(punkt, snap_til_shapely)[1]
            snappet_punkt = snap(punkt, nearest, tolerance=maks_distanse)
            punkter.iloc[i] = snappet_punkt
        
    return(punkter)


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


# teller opp antall nærliggende eller overlappende (hvis avstan=0) geometrier i to geodataframes.
# gdf1 returneres med en ny kolonne ('antall') som forteller hvor mange geometrier (rader) fra gdf2 som er innen spesifisert avstand. 
def antall_innen_avstand(gdf1: gpd.GeoDataFrame,
                         gdf2: gpd.GeoDataFrame,
                         avstand=0,
                         kolonnenavn="antall") -> gpd.GeoDataFrame:

    #lag midlertidig ID
    gdf1["min_iddd"] = range(len(gdf1))

    gdf1_kopi = gdf1.copy(deep=True)
    gdf2_kopi = gdf2.copy(deep=True)

    #buffer paa gdf2
    if avstand>0:
        gdf2_kopi["geometry"] = gdf2_kopi.buffer(avstand)
    
    #join med relevante kolonner
    gdf1_kopi = gdf1_kopi[["min_iddd", "geometry"]]
    gdf2_kopi = gdf2_kopi[["geometry"]]
    joined = gpd.sjoin(gdf1_kopi, gdf2_kopi, how="inner")

    #tell opp antall overlappende gdf2-geometrier, gjor om NA til 0 og sorg for at kolonnen er integer (heltall)
    joined[kolonnenavn] = joined['min_iddd'].map(joined['min_iddd'].value_counts()).fillna(0).astype(int)

    #fjern duplikater
    joined = joined.drop_duplicates("min_iddd")

    #koble kolonnen 'antall' til den opprinnelige gdf1
    joined = pd.DataFrame(joined[['min_iddd',kolonnenavn]])
    gdf1 = gdf1.drop([kolonnenavn], axis=1, errors='ignore') #fjern kolonnen antall hvis den allerede finnes i inputen
    gdf1 = gdf1.merge(joined, on = 'min_iddd', how = 'left')

    #fjern midlertidig ID
    gdf1 = gdf1.drop("min_iddd",axis=1)

    return(gdf1)


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
