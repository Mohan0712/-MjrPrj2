# backend/utils/geo_utils.py
import math

def haversine_km(lat1, lon1, lat2, lon2):
    # guard
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 1e9
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c
