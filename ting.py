import geopandas as gpd

# lager n tilfeldige punkter innenfor et gitt område (mask)
def tilfeldige_punkter(n, mask=None):
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