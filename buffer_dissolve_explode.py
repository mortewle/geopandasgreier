import geopandas as gpd


"""
Funksjoner som bufrer, dissolver og/eller gjør om fra multipart til singlepart (explode)

Gjelder for alle funksjonene:
 - høyere buffer-oppløsning enn standard
 - reparerer geometrien etter buffer og dissolve, men ikke etter explode, siden reparering kan returnere multipart-geometrier
 - index ignoreres og resettes alltid og kolonner som har med index å gjøre fjernes fordi de kan gi unødvendige feilmeldinger
 - hvis ikke 'by' spesifiseres når dissolve brukes, returneres bare geometrikolonnen og eventuelt id-kolonne
"""


def buff(gdf, avstand, 
         resolution=50, 
         copy=True, # kopiering tar mer plass i minnet, så greit å kunne unngå det hvis man vil
         **qwargs) -> gpd.GeoDataFrame:
    """ 
    buffer med høyere oppløsning 
    returnerer kopi av GeoDataFrame (hvis GeoDataFrame er input, ellers GeoSeries/shapely-objekt)
    """
    
    if copy:
        gdf = gdf.copy()
    if isinstance(gdf, gpd.GeoDataFrame):
        gdf["geometry"] = gdf.buffer(avstand, resolution=resolution, **qwargs)
        gdf["geometry"] = gdf.make_valid()
    else:
        gdf = gdf.buffer(avstand, resolution=resolution, **qwargs)
        gdf = gdf.make_valid()
    return gdf

 
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
    """ explode (til singlepart) som ignorerer index som default (samme som i pandas) """
    return gdf.explode(ignore_index=ignore_index, **qwargs)


from pandas.core.base import PandasObject
PandasObject.buff = buff
PandasObject.diss = diss
PandasObject.exp = exp


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
        singlepart = (gdf
                    .buff(avstand, resolution)
                    .diss(by, **diss_qwargs)
                    .exp()
        )
    else:
        bufret_dissolvet = gdf.buffer(avstand, resolution=resolution).unary_union
        singlepart = (gpd.GeoDataFrame({"geometry": gpd.GeoSeries(bufret_dissolvet)})
                      .set_crs(gdf.crs)
                      .make_valid()
                      .explode(ignore_index=True, index_parts=False)
                      )
        
    if id:
        singlepart[id] = list(range(len(singlepart)))
    
    return singlepart


# dissolve, explode (til singlepart). Altså dissolve overlappende.
# hvis 'by' ikke oppgis, returneres bare geometri-kolonnen og evt id-felt.
def dissexp(gdf, by=None, id=None, **qwargs) -> gpd.GeoDataFrame: 

    if by:
        singlepart = gdf.diss(by, **qwargs).exp()
    else:
        singlepart = (gpd.GeoDataFrame({"geometry": gpd.GeoSeries(gdf.unary_union)})
                      .set_crs(gdf.crs)
                      .make_valid()
                      .explode(ignore_index=True, index_parts=False)
                      )
        
    if id:
        singlepart[id] = list(range(len(singlepart)))
    
    return singlepart



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

    return dissolvet


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
