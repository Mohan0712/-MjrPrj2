# backend/routes/ambulances.py
from flask import Blueprint, current_app, request, jsonify

ambulance_bp = Blueprint("ambulance_bp", __name__)

@ambulance_bp.route("/nearest", methods=["POST"])
def nearest_ambulance():
    """
    Body: { latitude, longitude }
    Returns nearest available ambulance (status == 'available')
    """
    data = request.get_json(force=True)
    lat = data.get("latitude")
    lon = data.get("longitude")
    if lat is None or lon is None:
        return jsonify(success=False, message="latitude/longitude required"), 400

    col = current_app.config["DB_OPS"]["ambulances"]
    ambs = list(col.find({"status": "available"}, {"unit_id": 1, "latitude": 1, "longitude": 1}))
    if not ambs:
        return jsonify(success=False, message="No available ambulances"), 200

    from ..utils.geo_utils import haversine_km
    for a in ambs:
        a["distance"] = haversine_km(lat, lon, a.get("latitude"), a.get("longitude"))
    ambs.sort(key=lambda x: x["distance"])
    a0 = ambs[0]
    return jsonify(success=True, ambulance={
        "unit_id": a0.get("unit_id"),
        "latitude": a0.get("latitude"),
        "longitude": a0.get("longitude"),
        "distance": round(a0.get("distance", 0), 2)
    })


@ambulance_bp.route("/track/<unit_id>", methods=["GET"])
def track(unit_id):
    """
    Returns the last known position of an ambulance.
    Expect your background job/device to keep updating DB_OPS.ambulances positions.
    """
    col = current_app.config["DB_OPS"]["ambulances"]
    doc = col.find_one({"unit_id": unit_id}, {"_id": 0, "unit_id": 1, "latitude": 1, "longitude": 1, "status": 1, "last_location_update": 1})
    if not doc:
        return jsonify(success=False, message="Not found"), 404
    return jsonify(success=True, ambulance=doc)
