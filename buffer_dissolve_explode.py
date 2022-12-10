import geopandas as gpd
import numpy as np
from pandas.core.base import PandasObject


"""
Funksjoner som bufrer, dissolver og/eller gjør om fra multipart til singlepart (explode)

Gjelder for alle funksjonene:
 - høyere buffer-oppløsning enn standard
 - reparerer geometrien etter buffer og dissolve, men ikke etter explode, siden reparering kan returnere multipart-geometrier
 - index ignoreres og resettes alltid og kolonner som har med index å gjøre fjernes fordi de kan gi unødvendige feilmeldinger
 - hvis ikke 'by' spesifiseres når dissolve brukes, returneres bare geometrikolonnen og eventuelt id-kolonne
"""


def buff(gdf, avstand, resolution=50, **qwargs) -> gpd.GeoDataFrame:
    """ buffer med høyere oppløsning som returnerer kopi av GeoDataFrame (hvis GeoDataFrame er input, ellers GeoSeries/shapely-objekt)"""

    kopi = gdf.copy()
    if isinstance(gdf, gpd.GeoDataFrame):
        kopi["geometry"] = kopi.buffer(avstand, resolution=resolution, **qwargs)
        kopi["geometry"] = kopi.make_valid()
    else:
        kopi = kopi.buffer(avstand, resolution=resolution, **qwargs)
        kopi = kopi.make_valid()
    return kopi

 
def diss(gdf, by=None, aggfunc = "sum", **qwargs) -> gpd.GeoDataFrame:
    """ 
    dissolve som ignorerer og resetter index
    med aggfunc='sum' som default fordi 'first' gir null mening
    hvis flere aggfuncs, gjøres kolonnene om til string, det vil si fra (kolonne, sum) til kolonne_sum
    """

#    if aggfunc=="sum":
 #       aggfunc = {col: "sum" for col, dtype in zip(gdf.columns, gdf.dtypes)
  #                  if "float" in str(dtype) or "int" in str(dtype)}
        
    dissolvet = (gdf
                 .loc[:, ~gdf.columns.str.contains('index|level_')]
                 .dissolve(by=by, aggfunc=aggfunc, **qwargs)
                 .reset_index()
    )
            
    dissolvet["geometry"] = dissolvet.make_valid()
    
    # legg til aggfunc i kolonnenavnet
    if isinstance(aggfunc, dict):
        dissolvet.columns = [col+"_"+aggfunc[col] if col in aggfunc else col for col in dissolvet.columns]
                
    # gjør kolonner fra tuple til string
    dissolvet.columns = ["_".join(kolonne).strip("_") 
                         if isinstance(kolonne, tuple) else kolonne 
                         for kolonne in dissolvet.columns]

    return dissolvet.loc[:, ~dissolvet.columns.str.contains('index|level_')]


def exp(gdf, ignore_index=True, **qwargs) -> gpd.GeoDataFrame:
    """ explode (til singlepart) som ignorerer index som default """
    return gdf.explode(ignore_index=ignore_index, **qwargs)


# bufrer og samler overlappende. Altså buffer, dissolve, explode (til singlepart). 
# hvis 'by' ikke oppgis, returneres bare geometri-kolonnen og evt id-felt (siden det sjelden blir riktig å beholde kolonner etter dissolve og explode)
def buffdissexp(gdf,
                avstand, #buffer-avstand
                resolution=50, #oppløsningen på bufringen
                by = None, 
                id=None, 
                **diss_qwargs # flere dissolve-argumenter
                ) -> gpd.GeoDataFrame: 

    if by:
        kopi = gdf.copy()
        kopi["geometry"] = kopi.buffer(avstand, resolution=resolution).buffer(0)
        kopi = kopi.loc[:, ~kopi.columns.str.contains('index|level_')]
        dissolvet = kopi.dissolve(**diss_qwargs)
        kopi["geometry"] = kopi.buffer(0)
        dissolvet = dissolvet.reset_index()
        dissolvet.columns = ["_".join(kolonne).strip("_") 
                            if isinstance(kolonne, tuple) else kolonne 
                            for kolonne in dissolvet.columns]

        singlepart = dissolvet.loc[:, ~dissolvet.columns.str.contains('index|level_')]
    
    if by is None:
        #dissolver her før buffer fordi det er raskere
        dissolvet_bufret = gdf.unary_union.buffer(avstand, resolution=resolution).buffer(0)
        singlepart = (gpd.GeoDataFrame({"geometry": gpd.GeoSeries(dissolvet_bufret)}).set_crs(gdf.crs)
                      .explode(ignore_index=True, index_parts=False)
                      )
        
    if id:
        singlepart[id] = list(range(len(singlepart)))
    
    return singlepart


# dissolve, explode (til singlepart). Altså dissolve overlappende.
# hvis 'by' ikke oppgis, returneres bare geometri-kolonnen og evt id-felt.
def dissexp(gdf, by=None, id=None, **qwargs) -> gpd.GeoDataFrame: 

    if by:
        dissolvet = gdf.diss(by=by, **qwargs)
        singlepart = dissolvet.exp()
        
    if by is None:
        dissolvet = gdf.unary_union
        dissolvet_gdf = gpd.GeoDataFrame({"geometry": gpd.GeoSeries(dissolvet)}).set_crs(gdf.crs)
        dissolvet_gdf["geometry"] = dissolvet_gdf.geometry.apply(lambda x: x.buffer(0) if x.buffer(0).is_empty==False else x)
        singlepart = dissolvet_gdf.explode(ignore_index=True, index_parts=False)
        
    if id:
        singlepart[id] = list(range(len(singlepart)))
    
    return(singlepart)



# buffer, dissolve. 
# hvis 'by' ikke oppgis, returneres bare geometri-kolonnen og evt id-felt.
# 'aggfunc' brukes bare hvis 'by' oppgis.
def buffdiss(gdf,
             avstand, #buffer-avstand
             resolution=50, #oppløsningen på bufringen
             by = None, 
             id=None, 
             **diss_qwargs # flere dissolve-argumenter
             ) -> gpd.GeoDataFrame: 

    if by:
        bufret = gdf.buff(avstand, resolution)
        dissolvet = bufret.diss(by=by, **diss_qwargs)
        
    if by is None:
        dissolvet = gdf.unary_union.buffer(avstand, resolution=resolution).buffer(0)
        dissolvet = gpd.GeoDataFrame({"geometry": gpd.GeoSeries(dissolvet)}).set_crs(gdf.crs)
        
    if id:
        dissolvet[id] = list(range(len(dissolvet)))
    
    return(dissolvet)



#buffer, dissolve, tett indre hull i polygonene, bufre innover, singlepart.
def buffutinn(gdf,
              avstand, #buffer-avstand
              resolution=50, #oppløsningen på bufringen
              by = None, 
              id=None, 
              tett_hull=True,
              **diss_qwargs # flere dissolve-argumenter
              ) -> gpd.GeoDataFrame:

    from shapely.geometry import Polygon

    bufret = gdf.buff(avstand, resolution)
    dissolvet = bufret.diss(by = by, **diss_qwargs)
        
    if tett_hull:
        dissolvet.geometry = dissolvet.geometry.apply(lambda x: Polygon(x.exterior.coords))

    antibufret = dissolvet.buff(avstand*-1, resolution)
    singlepart = antibufret.exp()

    if id:
        singlepart[id] = list(range(len(singlepart)))

    return singlepart


# samler også overlappende geometrier innad i hver rad, men samler ikke rader. 
def tett_hull(geom, max_km2=None):

    from shapely import polygons, get_exterior_ring, get_parts, get_num_interior_rings, get_interior_ring, area, unary_union
    
    # tettingen gjøres i shapely og apply-es på hver rad av inputen.
    def tett_i_shapely(x, max_km2=max_km2):
                
        # hvis alle hull skal tettes, lages det polygon av yttergrensene
        if max_km2 is None:
            hull_tettet = polygons(get_exterior_ring(get_parts(x)))
            return unary_union(hull_tettet)

        #hvis ikke alle hull skal tettes, gjøres hvert hull til polygon og appendes til lista hull_tettet hvis de er mindre enn max_km2. Så samles alt.
        hull_tettet = [x]
        singlepart = get_parts(x)
        for part in singlepart:
            antall_indre_ringer = get_num_interior_rings(part)
            if antall_indre_ringer>0:
                for n in range(antall_indre_ringer):
                    hull = polygons(get_interior_ring(part, n))
                    if area(hull)/1000000 < max_km2:
                        hull_tettet.append(hull)
        return unary_union(hull_tettet)

    if isinstance(geom, gpd.GeoDataFrame):
        kopi = geom.copy(deep=True)
        kopi["geometry"] = kopi.geometry.map(lambda x: tett_i_shapely(x, max_km2))

    elif isinstance(geom, gpd.GeoSeries):
        kopi = geom.copy()
        kopi = kopi.map(lambda x: tett_i_shapely(x, max_km2))
        kopi = gpd.GeoSeries(kopi)

    else: #hvis geom er shapely-objekt/array
        kopi = tett_i_shapely(geom, max_km2)

    return kopi