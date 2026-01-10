import requests
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var is required")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Workout(db.Model):
    __tablename__ = "workout"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    sets = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.PickleType, nullable=False)
    extra_weight = db.Column(db.PickleType, nullable=True)
    is_bodyweight = db.Column(db.Boolean, nullable=False)
    exercise_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)


class Exercise(db.Model):
    __tablename__ = "exercise"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "user_id": self.user_id}


TIMEZONEDB_API_KEY = os.getenv("TIMEZONEDB_API_KEY")
DEFAULT_TZ = os.getenv("DEFAULT_TZ", "Europe/Ljubljana")


@app.get("/external/time")
def external_time():
    if not TIMEZONEDB_API_KEY:
        return jsonify({"error": "TIMEZONEDB_API_KEY is not set"}), 500

    tz = request.args.get("tz") or DEFAULT_TZ

    url = "http://api.timezonedb.com/v2.1/get-time-zone"
    params = {
        "key": TIMEZONEDB_API_KEY,
        "format": "json",
        "by": "zone",
        "zone": tz
    }

    r = requests.get(url, params=params, timeout=5)
    r.raise_for_status()
    data = r.json()

    if data.get("status") != "OK":
        return jsonify({"error": "TimeZoneDB failed", "details": data}), 502

    return jsonify({
        "timezone": data.get("zoneName"),
        "country": data.get("countryName"),
        "formatted": data.get("formatted"),
        "timestamp": data.get("timestamp"),
        "source": "timezonedb"
    }), 200


@app.get("/api/workouts")
def api_workouts():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    workouts = Workout.query.filter_by(user_id=user_id).all()
    return jsonify([
        {
            "id": w.id,
            "date": w.date.isoformat(),
            "sets": w.sets,
            "reps": w.reps,
            "extra_weight": w.extra_weight,
            "is_bodyweight": w.is_bodyweight,
            "exercise_id": w.exercise_id,
            "user_id": w.user_id
        } for w in workouts
    ])


@app.get("/api/exercises")
def api_exercises():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    exercises = Exercise.query.filter_by(user_id=user_id).all()
    return jsonify([e.to_dict() for e in exercises])


@app.get("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "UP"}), 200
    except Exception as e:
        return jsonify({"status": "DOWN", "error": str(e)}), 500


@app.get("/stats/summary")
def summary_for_user():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id query param is required"}), 400

    workouts = Workout.query.filter_by(user_id=user_id).all()
    total_workouts = len(workouts)
    total_sets = sum(w.sets for w in workouts)

    total_reps = 0
    total_tonnage = 0.0

    for w in workouts:
        reps_list = w.reps or []
        weights_list = w.extra_weight or []
        for i in range(min(len(reps_list), len(weights_list))):
            r = reps_list[i] or 0
            wt = weights_list[i] or 0
            total_reps += int(r)
            total_tonnage += float(r) * float(wt)

    return jsonify({
        "user_id": user_id,
        "total_workouts": total_workouts,
        "total_sets": total_sets,
        "total_reps": total_reps,
        "total_tonnage": total_tonnage,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    })


@app.get("/stats/workouts")
def workouts_for_user():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id query param is required"}), 400

    workouts = Workout.query.filter_by(
        user_id=user_id).order_by(Workout.date.asc()).all()
    return jsonify([
        {
            "id": w.id,
            "date": w.date.isoformat(),
            "sets": w.sets,
            "reps": w.reps,
            "extra_weight": w.extra_weight,
            "is_bodyweight": w.is_bodyweight,
            "exercise_id": w.exercise_id,
            "user_id": w.user_id
        } for w in workouts
    ])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
