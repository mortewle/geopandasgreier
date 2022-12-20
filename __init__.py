""" ort """
from geopandasgreier.buffer_dissolve_explode import buff, diss, exp, buffdiss, dissexp, buffdissexp, tett_hull
from geopandasgreier.generelt import *
from geopandasgreier.spesifikt import *


#gjør at funksjonene kan brukes som metoder sånn som i pandas, altså at man skriver gdf.funksjon heller enn funksjon(gdf)
#from pandas.core.base import PandasObject
#PandasObject.buffdissexp = buffdissexp
#PandasObject.buffdiss = buffdiss
#PandasObject.dissexp = dissexp
#PandasObject.buff = buff
#PandasObject.diss = diss
#PandasObject.exp = exp
#PandasObject.tett_hull = tett_hull


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
