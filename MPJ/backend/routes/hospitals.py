from flask import Blueprint, current_app, request, jsonify
from ..utils.geo_utils import haversine_km

hospital_bp = Blueprint("hospital_bp", __name__)

def _as_float(v):
    try:
        return float(v)
    except Exception:
        return None

@hospital_bp.route("/nearest", methods=["POST"])
def nearest():
    """
    Body: { latitude, longitude }
    Returns: top 5 nearest hospitals (name, address, distance_km, specialties)
    """
    data = request.get_json(force=True)
    lat = _as_float(data.get("latitude"))
    lon = _as_float(data.get("longitude"))

    if lat is None or lon is None:
        return jsonify(success=False, message="latitude/longitude required (numeric)"), 400

    col = current_app.config["DB_HOSPITAL"]["bangalore_hospitals"]
    total = col.count_documents({})
    if total == 0:
        return jsonify(success=False, message="bangalore_hospitals collection is empty"), 200

    cursor = col.find({}, {"name": 1, "address": 1, "latitude": 1, "longitude": 1, "specialties": 1})
    hospitals = []
    skipped_no_coords = 0

    for doc in cursor:
        hlat = _as_float(doc.get("latitude"))
        hlon = _as_float(doc.get("longitude"))
        if hlat is None or hlon is None:
            skipped_no_coords += 1
            continue
        dist = haversine_km(lat, lon, hlat, hlon)
        hospitals.append({
            "id": str(doc.get("_id")),
            "name": doc.get("name"),
            "address": doc.get("address"),
            "latitude": hlat,
            "longitude": hlon,
            "distance": round(dist, 2),
            "specialties": (doc.get("specialties") or [])[:5]
        })

    hospitals.sort(key=lambda x: x["distance"])
    return jsonify(
        success=True,
        hospitals=hospitals[:5],
        meta={"total_in_db": total, "skipped_no_coords": skipped_no_coords}
    )

@hospital_bp.route("/all", methods=["GET"])
def all_hospitals():
    col = current_app.config["DB_HOSPITAL"]["bangalore_hospitals"]
    cursor = col.find({}, {"name": 1, "address": 1, "specialties": 1})
    out = [{"id": str(d["_id"]), "name": d.get("name"), "address": d.get("address"),
            "specialties": (d.get("specialties") or [])[:5]} for d in cursor]
    return jsonify(success=True, hospitals=out)
