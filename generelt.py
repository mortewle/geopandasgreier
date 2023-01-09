"""
Ymse funksjoner som kan brukes med geopandas.
"""
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.wkt import loads


def fjern_tomme_geometrier(gdf):
    """ fjerner tomme geometrier og NaN-geometrier. """
    
    if isinstance(gdf, gpd.GeoDataFrame):
        gdf = gdf[~gdf.geometry.is_empty]
        gdf = gdf.dropna(subset = ["geometry"])
    elif isinstance(gdf, gpd.GeoSeries):
        gdf = gdf[~gdf.is_empty]
        gdf = gdf.dropna()
    else:
        raise ValueError("Input må være GeoDataFrame eller GeoSeries")
    return gdf


def gdf_concat(gdf_liste: list, crs=None, axis=0, ignore_index=True, geometry="geometry", **concat_qwargs) -> gpd.GeoDataFrame:
    """ 
    Samler liste med geodataframes til en lang geodataframe.
    Ignorerer index, endrer til samme crs. """
    
    for i, gdf in enumerate(gdf_liste):
        if len(gdf)==0:
            raise ValueError(f"{i}. gdf-en har 0 rader.")
    
    if not crs:
        crs = gdf_liste[0].crs
        
    try:
        gdf_liste = [gdf.to_crs(crs) for gdf in gdf_liste]
    except ValueError:
        print("OBS: ikke alle gdf-ene dine har crs. Hvis du nå samler latlon og utm, må du først bestemme crs med set_crs(), så gi dem samme crs med to_crs()")

    return gpd.GeoDataFrame(pd.concat(gdf_liste, axis=axis, ignore_index=ignore_index, **concat_qwargs), geometry=geometry, crs=crs)


def til_gdf(geom, crs=None, **qwargs) -> gpd.GeoDataFrame:
    """ 
    Konverterer til geodataframe fra geoseries, shapely-objekt, wkt, liste med shapely-objekter eller shapely-sekvenser 
    OBS: når man har shapely-objekter eller wkt, bør man velge crs. """

    if not crs:
        if isinstance(geom, str):
            raise ValueError("Du må bestemme crs når input er string.")
        crs = geom.crs
        
    if isinstance(geom, str):
        from shapely.wkt import loads
        geom = loads(geom)
        gdf = gpd.GeoDataFrame({"geometry": gpd.GeoSeries(geom)}, crs=crs, **qwargs)
    else:
        gdf = gpd.GeoDataFrame({"geometry": gpd.GeoSeries(geom)}, crs=crs, **qwargs)
    
    return gdf


def overlay_update(gdf1, gdf2) -> gpd.GeoDataFrame:
    """ En overlay-variant som ikke finnes i geopandas. """
    
    out = gdf1.overlay(gdf2, how = "difference", keep_geom_type=True)
    out = out.loc[:, ~out.columns.str.contains('index|level_')]
    out = gdf_concat([out, gdf2])
    return out


def min_sjoin(left_gdf, right_gdf, fjern_dupkol = True, **kwargs) -> gpd.GeoDataFrame:
    """ 
    som gpd.sjoin bare at kolonner i right_gdf som også er i left_gdf fjernes (fordi det snart vil gi feilmelding i geopandas)
    og kolonner som har med index å gjøre fjernes, fordi sjoin returnerer index_right som kolonnenavn, som gir feilmelding ved neste join. 
    """

    #fjern index-kolonner
    left_gdf = left_gdf.loc[:, ~left_gdf.columns.str.contains('index|level_')]
    right_gdf = right_gdf.loc[:, ~right_gdf.columns.str.contains('index|level_')]

    #fjern kolonner fra gdf2 som er i gdf1
    if fjern_dupkol:
        right_gdf.columns = [col if col not in left_gdf.columns or col=="geometry" else "skal_fjernes" for col in right_gdf.columns]
        right_gdf = right_gdf.loc[:, ~right_gdf.columns.str.contains('skal_fjernes')]

    joinet = left_gdf.sjoin(right_gdf, **kwargs).reset_index()
        
    return joinet.loc[:, ~joinet.columns.str.contains('index|level_')]


def kartlegg(gdf, kolonne=None, scheme="Quantiles", tittel=None, storrelse=15, fontsize=16, legend=True, alpha=0.7, **qwargs) -> None:
    """ Enkel, statisk kartlegging. """
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, figsize=(storrelse, storrelse))
    ax.set_axis_off()
    ax.set_title(tittel, fontsize = fontsize)
    gdf.plot(kolonne, scheme=scheme, legend=legend, alpha=alpha, ax=ax, **qwargs)


def tilfeldige_punkter(n: int, mask=None) -> gpd.GeoDataFrame:
    """ lager n tilfeldige punkter innenfor et gitt område (mask). """
    
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
