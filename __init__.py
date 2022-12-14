""" ort """

import os
os.environ['USE_PYGEOS'] = '0'


# først noen kjappe tester av funksjonene og de underliggende GIS-algoritmene
from geopandasgreier.testing.test import test_alt

import pandas as pd
pd.options.mode.chained_assignment = None # ignorerer midlertidig SettingWithCopyWarning

try:
    test_alt()
except Exception as e:
    print(f"OBS: klarte ikke geopandasgreier-testene: {str(e)}")
    print("Sjekk geopandasgreier.testing.test for mer detaljer.")
        
pd.options.mode.chained_assignment = 'warn'

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

from geopandasgreier.lesing_lagring import (
    les_geopandas, 
    skriv_geopandas,
    eksisterer,
    samle_filer,
)