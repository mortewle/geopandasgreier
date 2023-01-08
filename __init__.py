""" ort """

import os
os.environ['USE_PYGEOS'] = '0'
import geopandas as gpd

# først noen kjappe tester av funksjonene og de underliggende GIS-algoritmene
from geopandasgreier.testing.test import test_alt
try:
    test_alt()
except Exception as e:
    print("OBS: klarte ikke geopandasgreier-testene:")
    print(e)
    print("Sjekk geopandasgreier.testing.test for mer detaljer.")

del test_alt


from geopandasgreier.buffer_dissolve_explode import (
    buff, 
    diss, 
    exp, 
    buffdissexp, 
    buffdiss, 
    dissexp, 
    tett_hull
)

from geopandasgreier.generelt import (
    til_gdf, 
    gdf_concat, 
    fjern_tomme_geometrier
)

from geopandasgreier.spesifikt import (
    gridish,
)