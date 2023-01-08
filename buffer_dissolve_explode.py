import pandas as pd
import geopandas as gpd


"""
Funksjoner som bufrer, dissolver og/eller gjør om fra multipart til singlepart (explode)

Regler for alle funksjonene:
 - høyere buffer-oppløsning enn standard
 - reparerer geometrien etter buffer og dissolve, men ikke etter explode, siden reparering kan returnere multipart-geometrier
 - index ignoreres og resettes alltid og kolonner som har med index å gjøre fjernes fordi de kan gi unødvendige feilmeldinger
 - hvis ikke 'by' spesifiseres når dissolve brukes, returneres bare geometrikolonnen og eventuelt id-kolonne
"""


def buff(gdf, avstand, resolution=50, copy=False, **qwargs) -> gpd.GeoDataFrame:
    """
    buffer med høyere oppløsning som reparerer geometrien.
    returnerer GeoDataFrame hvis GeoDataFrame er input, ellers GeoSeries/shapely-objekt.
    copy=False som default for å spare minne.
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


def diss(gdf, by=None, aggfunc="sum", **qwargs) -> gpd.GeoDataFrame:
    """
    dissolve som ignorerer og resetter index
    med aggfunc='sum' som default fordi 'first' gir null mening
    hvis flere aggfuncs, gjøres kolonnene om til string, det vil si fra (kolonne, sum) til kolonne_sum
    """

    dissolvet = (gdf
                 .loc[:, ~gdf.columns.str.contains("index|level_")]
                 .dissolve(by=by, aggfunc=aggfunc, **qwargs)
                 .reset_index()
    )

    dissolvet["geometry"] = dissolvet.make_valid()

    # gjør kolonner fra tuple til string
    dissolvet.columns = ["_".join(kolonne).strip("_") if isinstance(kolonne, tuple) else kolonne for kolonne in dissolvet.columns]

    return dissolvet


# denne funksjonen trengs egentlig ikke, bare la den til for å være konsistent med opplegget med buff, diss og exp
def exp(gdf, ignore_index=True, **qwargs) -> gpd.GeoDataFrame:
    """ 
    explode (til singlepart) som reparerer geometrien og ignorerer index som default (samme som i pandas). 
    reparerer før explode fordi reparering kan skape multigeometrier. 
    """
    gdf["geometry"] = gdf.make_valid()
    return gdf.explode(ignore_index=ignore_index, **qwargs)


def buffdissexp(gdf, avstand, resolution=50, by=None, id=None, copy=False, **dissolve_qwargs) -> gpd.GeoDataFrame:
    """
    Bufrer og samler overlappende. Altså buffer, dissolve, explode (til singlepart).
    avstand: buffer-avstand
    resolution: buffer-oppløsning
    by: dissolve by
    id: navn på eventuell id-kolonne
    """

    if by:
        bufret = buff(gdf, avstand, resolution=resolution, copy=copy)
        dissolvet = diss(bufret, by=by, **dissolve_qwargs)
        singlepart = dissolvet.explode(ignore_index=True)

    else:
        bufret = gdf.buffer(avstand, resolution=resolution)
        dissolvet = gpd.GeoDataFrame({"geometry": gpd.GeoSeries(bufret.unary_union)}, geometry="geometry", crs=gdf.crs)
        dissolvet["geometry"] = dissolvet.make_valid()
        singlepart = dissolvet.explode(ignore_index=True)

    if id:
        singlepart[id] = list(range(len(singlepart)))

    return singlepart


def dissexp(gdf, by=None, id=None, **qwargs) -> gpd.GeoDataFrame:
    """
    Dissolve, explode (til singlepart). Altså dissolve overlappende.
    Hvis 'by' ikke oppgis, returneres bare geometri-kolonnen og evt id-felt.
    resolution: buffer-oppløsning
    by: dissolve by
    id: navn på eventuell id-kolonne
    """

    if by:
        dissolvet = diss(gdf, by, **qwargs)
        singlepart = dissolvet.explode(ignore_index=True)
    else:
        dissolvet = gpd.GeoDataFrame(pd.DataFrame({"geometry": gpd.GeoSeries(bufret.unary_union)}), geometry="geometry", crs=gdf.crs)
        dissolvet["geometry"] = dissolvet.make_valid()
        singlepart = dissolvet.explode(ignore_index=True)

    if id:
        singlepart[id] = list(range(len(singlepart)))

    return singlepart


def buffdiss(gdf, avstand, resolution=50, by=None, id=None, copy = False, **dissolve_qwargs) -> gpd.GeoDataFrame:
    """
    Buffer, dissolve.
    Hvis 'by' ikke oppgis, returneres bare geometri-kolonnen og evt id-felt.
    """
    
    if by:
        bufret = buff(gdf, avstand, resolution, copy)
        dissolvet = diss(bufret, by, **dissolve_qwargs)

    if by is None:
        bufret = gdf.buffer(avstand, resolution=resolution)
        dissolvet = gpd.GeoDataFrame(pd.DataFrame({"geometry": gpd.GeoSeries(bufret.unary_union)}), geometry="geometry", crs=gdf.crs)
        dissolvet["geometry"] = dissolvet.make_valid()

    if id:
        dissolvet[id] = list(range(len(dissolvet)))

    return dissolvet


def tett_hull(geom, max_km2=None, copy=False):
    """
    Tetter hull inni polygoner. Kun hull under max_km2 hvis max_km2 er oppgitt.
    Samler også overlappende geometrier innad i hver rad, men samler ikke rader.
    """

    from shapely import (
        polygons,
        get_exterior_ring,
        get_parts,
        get_num_interior_rings,
        get_interior_ring,
        area,
    )
    from shapely.ops import unary_union

    if copy:
        gdf = gdf.copy()
        
    # tettingen gjøres i shapely og apply-es på hver rad av inputen.
    def tett_med_shapely(x, max_km2=max_km2):

        # hvis alle hull skal tettes, lages det polygon av yttergrensene
        if max_km2 is None:
            hull_tettet = polygons(get_exterior_ring(get_parts(x)))
            return unary_union(hull_tettet)

        # hvis ikke alle hull skal tettes, gjøres hvert hull til polygon og appendes til lista hull_tettet hvis de er mindre enn max_km2. Så samles alt.
        # kan antakelig forbedres veldig
        hull_tettet = [x]
        singlepart = get_parts(x)
        for part in singlepart:
            antall_indre_ringer = get_num_interior_rings(part)
            if antall_indre_ringer > 0:
                for n in range(antall_indre_ringer):
                    hull = polygons(get_interior_ring(part, n))
                    if area(hull) / 1_000_000 < max_km2:
                        hull_tettet.append(hull)
        return unary_union(hull_tettet)

    if isinstance(geom, gpd.GeoDataFrame):
        geom["geometry"] = geom.geometry.map(lambda x: tett_med_shapely(x, max_km2))

    elif isinstance(geom, gpd.GeoSeries):
        geom = geom.map(lambda x: tett_med_shapely(x, max_km2))
        geom = gpd.GeoSeries(geom)

    else:  # hvis geom er shapely-objekt/array
        geom = tett_med_shapely(geom, max_km2)

    return geom

