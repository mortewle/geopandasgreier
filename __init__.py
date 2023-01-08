""" ort """

# først noen kjappe tester av funksjonene og GIS-algoritmene
from geopandasgreier.testing.test import test_alt
try:
    test_alt()
except Exception as e:
    print("OBS: klarte ikke geopandasgreier-testene:")
    print(e)
    print("Sjekk geopandasgreier.testing.test for mer detaljer.")

del test_alt

from geopandasgreier.buffer_dissolve_explode import buff, diss, exp, buffdiss, dissexp, buffdissexp, tett_hull
from geopandasgreier.generelt import *
from geopandasgreier.spesifikt import *



#små støttefunksjoner


#decorator
def tidtagning(funksjon):
    def tiddd(*args, **kwargs):
        print(f"\nStarter '{funksjon.__name__}'")
        tid = time.perf_counter()
        out = funksjon(*args, **kwargs)
        print(f"'{funksjon.__name__}' ferdig etter {round((time.perf_counter()-tid)/60, 1)} min.\n")
        return out
    return tiddd

def logging(id, melding, loggfil):
    if not os.path.exists(loggfil):
        df = pd.DataFrame({"id": [], "melding":[]})
    else:
        df = pd.read_csv(loggfil, sep=";")
    ny_melding = pd.DataFrame({"id": [id], "melding": [str(melding)]})
    samlet = pd.concat([df, ny_melding], axis=0, ignore_index=True)
    samlet.to_csv(loggfil, sep=";", index=False)

def aaret_naa():
    import datetime
    return str(datetime.datetime.now().year)

#fra string til heltall
def til_int(series):
    return series.replace(r'^\s*$', np.nan, regex=True).replace(",",".").fillna(0).astype(float).astype(int)
