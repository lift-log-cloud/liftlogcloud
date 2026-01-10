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
