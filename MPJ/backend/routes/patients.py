# backend/routes/patients.py
from flask import Blueprint, current_app, request, jsonify
from datetime import datetime

patient_bp = Blueprint("patient_bp", __name__)

@patient_bp.route("/vitals", methods=["POST"])
def vitals():
    """
    Body: {
      patient_id, hospital_name, incident_id,
      vitals: {heart_rate, blood_pressure_systolic, blood_pressure_diastolic, oxygen_saturation, temperature, respiratory_rate}
    }
    """
    data = request.get_json(force=True)
    patient_id = data.get("patient_id")
    hospital_name = data.get("hospital_name")
    incident_id = data.get("incident_id")
    vitals = data.get("vitals", {})

    if not patient_id or not hospital_name or not vitals:
        return jsonify(success=False, message="patient_id, hospital_name, vitals required"), 400

    payload = {
        "patient_id": patient_id,
        "hospital_name": hospital_name,
        "incident_id": incident_id,
        "vitals": vitals,
        "created_at": datetime.utcnow()
    }
    col = current_app.config["DB_VITALS"]["records"]
    col.insert_one(payload)
    return jsonify(success=True)


@patient_bp.route("/recent", methods=["GET"])
def recent_vitals():
    col = current_app.config["DB_VITALS"]["records"]
    docs = col.find({}).sort("created_at", -1).limit(20)
    out = []
    for d in docs:
        out.append({
            "id": str(d["_id"]),
            "patient_id": d.get("patient_id"),
            "hospital_name": d.get("hospital_name"),
            "incident_id": d.get("incident_id"),
            "vitals": d.get("vitals"),
            "created_at": d.get("created_at")
        })
    return jsonify(success=True, records=out)
