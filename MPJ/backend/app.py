# backend/app.py
from pathlib import Path
from flask import Flask, render_template
from dotenv import load_dotenv
from pymongo import MongoClient
import os

# --- Load env
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# --- Flask app factory style (but single file for simplicity)
app = Flask(
    __name__,
    template_folder=str(Path(__file__).resolve().parents[1] / "frontend" / "templates"),
    static_folder=str(Path(__file__).resolve().parents[1] / "frontend" / "static")
)

# --- Mongo Client (single client, multiple DBs)
client = MongoClient(MONGO_URI)
db_hospital = client["hospital_db"]          # contains bangalore_hospitals, incidents (if you prefer)
db_vitals = client["patient_vitals"]         # for vitals
db_ops = client["operations_db"]             # for incidents & ambulances (clean separation)

# expose DBs to blueprints via app config
app.config["DB_HOSPITAL"] = db_hospital
app.config["DB_VITALS"] = db_vitals
app.config["DB_OPS"] = db_ops

# --- Blueprints
from .routes.hospitals import hospital_bp
from .routes.incidents import incident_bp
from .routes.patients import patient_bp
from .routes.ambulances import ambulance_bp

app.register_blueprint(hospital_bp, url_prefix="/api/hospitals")
app.register_blueprint(incident_bp, url_prefix="/api/incidents")
app.register_blueprint(patient_bp, url_prefix="/api/patients")
app.register_blueprint(ambulance_bp, url_prefix="/api/ambulances")

# --- Page routes (server-rendered)
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/report")
def report():
    return render_template("report_emergency.html")

@app.route("/hospitals")
def hospitals_page():
    return render_template("hospitals.html")

@app.route("/patients")
def patients_page():
    return render_template("patients.html")

@app.route("/incidents")
def incidents_page():
    return render_template("incidents.html")

if __name__ == "__main__":
    # IMPORTANT: run this app as a module in dev:
    # python -m backend.app
    app.run(host="0.0.0.0", port=5000, debug=True)
