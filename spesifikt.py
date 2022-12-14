import geopandas as gpd
import pandas as pd


def finn_naboer(gdf, mulige_naboer, id_kolonne, innen_meter = 1):
    """ 
    finner geometrier som er maks. 1 meter unna.
    i alle retninger (queen contiguity). """
    
    mulige_naboer = mulige_naboer.to_crs(25833)
    
    bufret = (gdf
              .to_crs(25833)
              .buffer(innen_meter)
              .to_frame()
    )
    
    joinet = bufret.sjoin(mulige_naboer, how="inner")
    
    return [x for x in joinet[id_kolonne].unique()]


def gridish(gdf, meter, x2 = False):
    """
    Enkel rutedeling av dataene. For å fleksibelt kunne loope for små områder sånn at ting blir håndterbart. 
    Gir dataene kolonne med avrundede xy-koordinater. Rundes av til valgfritt antall meter.
    x2=True gir en kolonne til med ruter 1/2 hakk nedover og bortover. Hvis grensetilfeller er viktig, kan man loope en gang per rutekategorikolonne. 
    """
    
    # rund ned koordinatene og sett sammen til kolonne
    gdf["gridish"] = [f"{round(minx/meter)}_{round(miny/meter)}" for minx, miny in zip(gdf.geometry.bounds.minx, gdf.geometry.bounds.miny)]
    
    if x2:

        gdf["gridish_x"] = gdf.geometry.bounds.minx / meter
        
        unike_x = gdf["gridish_x"].astype(int).unique()
        unike_x.sort()
        
        for x in unike_x:
            gdf.loc[(gdf["gridish_x"] >= x-0.5) & (gdf["gridish_x"] < x+0.5), "gridish_x2"] = x+0.5

        # samme for y
        gdf["gridish_y"] = gdf.geometry.bounds.miny/meter
        unike_y = gdf["gridish_y"].astype(int).unique()
        unike_y.sort()
        for y in unike_y:
            gdf.loc[(gdf["gridish_y"] >= y-0.5) & (gdf["gridish_y"] < y+0.5), "gridish_y2"] = y+0.5

        gdf["gridish2"] = gdf["gridish_x2"].astype(str) + "_" + gdf["gridish_y2"].astype(str)

        gdf = gdf.drop(["gridish_x","gridish_y","gridish_x2","gridish_y2"], axis=1)
        
    return gdf


def snap_til(punkter, snap_til, maks_distanse=500, copy=False):
    """
    Snapper (flytter) punkter til naermeste punkt/linje/polygon innen en gitt maks_distanse.
    Går via nearest_points for å finne det nøyaktige punktet. Med kun snap() blir det unøyaktig.
    Funker med geodataframes og geoseries. """
    
    from shapely.ops import nearest_points, snap

    snap_til_shapely = snap_til.unary_union
    
    if copy:
        punkter = punkter.copy()
        
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
        
    return punkter


def antall_innen_avstand(gdf1: gpd.GeoDataFrame,
                         gdf2: gpd.GeoDataFrame,
                         avstand=0,
                         kolonnenavn="antall") -> gpd.GeoDataFrame:
    """
    Teller opp antall nærliggende eller overlappende (hvis avstan=0) geometrier i to geodataframes.
    gdf1 returneres med en ny kolonne ('antall') som forteller hvor mange geometrier (rader) fra gdf2 som er innen spesifisert avstand. """

    #lag midlertidig ID
    gdf1["min_iddd"] = range(len(gdf1))


    #buffer paa gdf2
    if avstand>0:
        gdf2 = gdf2.copy()
        gdf2["geometry"] = gdf2.buffer(avstand)
    
    #join med relevante kolonner
    joined = gdf1[["min_iddd", "geometry"]].sjoin(gdf2[["geometry"]], how="inner")

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

    return gdf1


def til_multipunkt(geom, copy=False):

    from shapely.wkt import loads
    from shapely import force_2d
    from shapely.ops import unary_union
    
    if copy:
        geom = geom.copy()

    def til_multipunkt_i_shapely(geom):

        koordinater = ''.join([x for x in geom.wkt if x.isdigit() or x.isspace() or x=="." or x==","]).strip()

        alle_punkter = [loads(f"POINT ({punkt})") for punkt in koordinater.split(",")]

        return unary_union(alle_punkter)

    if isinstance(geom, gpd.GeoDataFrame):
        geom["geometry"] = force_2d(geom.geometry)
        geom["geometry"] = geom.geometry.apply(lambda x: til_multipunkt_i_shapely(x))

    elif isinstance(geom, gpd.GeoSeries):
        geom = force_2d(geom)
        geom = geom.apply(lambda x: til_multipunkt_i_shapely(x))

    else:
        geom = force_2d(geom)
        geom = til_multipunkt_i_shapely(unary_union(geom))

    return geom