# backend/routes/incidents.py
from flask import Blueprint, current_app, request, jsonify
from datetime import datetime

incident_bp = Blueprint("incident_bp", __name__)

@incident_bp.route("/report", methods=["POST"])
def report():
    """
    Body: { latitude, longitude, type, severity, description }
    Saves an incident and returns its ID.
    """
    data = request.get_json(force=True)
    lat = data.get("latitude")
    lon = data.get("longitude")
    itype = data.get("type")
    sev = data.get("severity")
    desc = data.get("description", "")

    if lat is None or lon is None or not itype or not sev:
        return jsonify(success=False, message="latitude, longitude, type, severity required"), 400

    payload = {
        "latitude": float(lat),
        "longitude": float(lon),
        "incident_type": itype,
        "severity": sev,
        "description": desc,
        "status": "detected",
        "created_at": datetime.utcnow()
    }
    col = current_app.config["DB_OPS"]["incidents"]
    result = col.insert_one(payload)
    return jsonify(success=True, incident_id=str(result.inserted_id))


@incident_bp.route("/recent", methods=["GET"])
def recent():
    col = current_app.config["DB_OPS"]["incidents"]
    docs = col.find({}).sort("created_at", -1).limit(20)
    out = []
    for d in docs:
        out.append({
            "id": str(d["_id"]),
            "type": d.get("incident_type"),
            "severity": d.get("severity"),
            "status": d.get("status"),
            "description": d.get("description", ""),
            "created_at": d.get("created_at")
        })
    return jsonify(success=True, incidents=out)
