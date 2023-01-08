#%%
import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.wkt import loads

import sys
while "geopandasgreier" not in os.listdir():
    os.chdir("../")
sys.path.append(os.getcwd())

from geopandasgreier.buffer_dissolve_explode import buff, diss, buffdiss, dissexp, buffdissexp


def lag_gdf():
    xs = [10.7497196, 10.7484624, 10.7480624, 10.7384624, 10.7374624, 10.7324624, 10.7284624]
    ys = [59.9281407, 59.9275268, 59.9272268, 59.9175268, 59.9165268, 59.9365268, 59.9075268]
    punkter = [f'POINT ({x} {y})' for x, y in zip(xs, ys)]

    linje = ["LINESTRING (10.7284623 59.9075267, 10.7184623 59.9175267, 10.7114623 59.9135267, 10.7143623 59.8975267, 10.7384623 59.900000, 10.720000 59.9075200)"]

    polygon = ["POLYGON ((10.74 59.92, 10.735 59.915, 10.73 59.91, 10.725 59.905, 10.72 59.9, 10.72 59.91, 10.72 59.91, 10.74 59.92))"]

    geometrier = loads(punkter + linje + polygon)

    gdf = gpd.GeoDataFrame({'geometry': gpd.GeoSeries(geometrier)}, geometry="geometry", crs=4326).to_crs(25833)
    gdf["numkol"] = [1,2,3,4,5,6,7,8,9]
    gdf["txtkol"] = [*'aaaabbbcc']
    
    assert gdf.dissolve().centroid.iloc[0].wkt == 'POINT (261106.48627792465 6649101.812189355)', "feil midtpunkt. Er testdataene endret?"
    
    assert len(gdf)==9, "feil lengde. Er testdataene endret?"

    return gdf


def test_buffdissexp():
    gdf = lag_gdf()
    for avstand in [1, 10, 100, 1000, 10000]:
        kopi = gdf.copy()
        kopi = kopi[["geometry"]]
        kopi = buff(kopi, avstand)
        kopi = diss(kopi)
        kopi = kopi.explode(ignore_index=True)

        areal1 = kopi.area.sum()
        lengde1 = kopi.length.sum()

        kopi = buff(gdf, avstand, copy=True)
        kopi = diss(kopi[["geometry"]])
        kopi = kopi.explode(ignore_index=True)

        assert areal1==kopi.area.sum() and lengde1==kopi.length.sum(), "ulik lengde/areal"

        kopi = buffdissexp(gdf, avstand, copy=True)

        assert areal1==kopi.area.sum() and lengde1==kopi.length.sum(), "ulik lengde/areal"


def test_geos():
    gdf = lag_gdf()
    kopi = buffdissexp(gdf, 25, copy=True)
    assert len(kopi)==4,  "feil antall rader. Noe galt/nytt med GEOS' GIS-algoritmer?"
    assert round(kopi.area.sum(), 5) == 1035381.10389, "feil areal. Noe galt/nytt med GEOS' GIS-algoritmer?"
    assert round(kopi.length.sum(), 5) == 16689.46148, "feil lengde. Noe galt/nytt med GEOS' GIS-algoritmer?"


def test_aggfuncs():
    gdf = lag_gdf()
    kopi = dissexp(gdf, by="txtkol", aggfunc="sum")
    assert len(kopi)==11, "dissexp by txtkol skal gi 11 rader, tre stykk linestrings..."

    kopi = buffdiss(gdf, 100, by="txtkol", aggfunc="sum", copy=True)
    assert kopi.numkol.sum() == gdf.numkol.sum() == sum([1,2,3,4,5,6,7,8,9])

    kopi = buffdissexp(gdf, 100, by="txtkol", aggfunc=["sum", "mean"], copy=True)
    assert "numkol_sum" in kopi.columns and "numkol_sum" in kopi.columns, "kolonnene følger ikke mønstret 'kolonnenavn_aggfunc'"
    assert len(kopi)==6, "feil lengde"

    kopi = buffdissexp(gdf, 1000, by="txtkol", aggfunc=["sum", "mean"], copy=True)
    assert len(kopi)==4, "feil lengde"

    kopi = buffdissexp(gdf, 100, by="numkol", copy=True)
    assert len(kopi)==9, "feil lengde"

    kopi = buffdissexp(gdf, 100, by=["numkol", "txtkol"],copy=True)
    assert "numkol" in kopi.columns and "txtkol" in kopi.columns, "kolonnene mangler. Er de index?"
    assert len(kopi)==9, "feil lengde"


def test_alt():
    
    test_buffdissexp()

    test_geos()

    test_aggfuncs()


if __name__=="__main__":
    
    info = """
    Testen ble lagd 08.01.2023 med følgende versjoner.
    Fra C++: GEOS 3.11.1, PROJ 9.1.0, GDAL 3.6.1. 
    Fra Python: geopandas 0.12.2, shapely 2.0.0, pyproj 3.4.1, pandas 1.5.2 og numpy 1.24.
    """
    print(info)
    
    print("Versjoner nå:")
    from shapely.geos import geos_version
    geos_versjon = ".".join([str(x) for x in geos_version])
    print(f'{gpd.__version__ = }')
    print(f'{geos_versjon    = }')
    print(f'{pd.__version__  = }')
    print(f'{np.__version__  = }')

    test_alt()

    print("vellykket")