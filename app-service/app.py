from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, Response
from tenacity import retry, retry_if_exception_type, wait_exponential, stop_after_attempt
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import datetime
from flasgger import Swagger
import pybreaker
import requests
import calendar
import bcrypt
import os

STATS_SERVICE_URL = os.getenv("STATS_SERVICE_URL", "http://stats:5000")

# 5 fails -> opens for 30s
stats_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30)

app = Flask(__name__)

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "LiftLog Core API",
        "description": "Core service endpoints (auth, workouts, exercises, proxy to stats).",
        "version": "1.0.0"
    }
}
Swagger(app, template=swagger_template)


load_dotenv("key.env")
app.secret_key = os.getenv('SECRET_KEY')

db_url = os.getenv("DATABASE_URL", "sqlite:///workouts.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    sets = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.PickleType, nullable=False)
    extra_weight = db.Column(db.PickleType, nullable=True)
    is_bodyweight = db.Column(db.Boolean, nullable=False)
    exercise_id = db.Column(
        db.Integer,
        db.ForeignKey('exercise.id', name='fk_workout_exercise_id'),
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', name='fk_workout_user_id'),
        nullable=False
    )

    exercise = db.relationship('Exercise', backref='workout')
    user = db.relationship('User', backref='workout')

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'sets': self.sets,
            'reps': self.reps,
            'extra_weight': self.extra_weight,
            'is_bodyweight': self.is_bodyweight,
            'exercise_id': self.exercise_id,
            'user_id': self.user_id
        }


class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', name='fk_exercise_user_id'),
        nullable=False
    )
    user = db.relationship('User', backref='excercise')

    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='uix_name_user'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id
        }


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    passwordHash = db.Column(db.String(255), nullable=False)


class UpstreamError(Exception):
    pass


# # TODO remove
# @app.route('/drop_all_tables')
# def drop_all_tables():
#     db.drop_all()
#     return "All tables dropped!"


def seedDB():
    Users = [
        User(username='user1', passwordHash='p1'),
        User(username='user2', passwordHash='p2'),
        User(username='user3', passwordHash='p3'),
    ]

    for user in Users:
        existingUser = User.query.filter_by(
            username=user.username, passwordHash=user.passwordHash).first()
        if not existingUser:
            db.session.add(user)

    db.session.commit()
    usr = User.query.filter_by(username='user1').first()
    exercises = [
        Exercise(name='bench press', user_id=usr.id),
        Exercise(name='squat', user_id=usr.id),
        Exercise(name='deadlift', user_id=usr.id),
        Exercise(name='pull-ups', user_id=usr.id),
        Exercise(name='push-ups', user_id=usr.id),
        Exercise(name='bicep curls', user_id=usr.id),
        Exercise(name='tricep dips', user_id=usr.id),
    ]
    for ex in exercises:
        existingEx = Exercise.query.filter_by(
            name=ex.name, user_id=ex.user_id).first()
        if not existingEx:
            db.session.add(ex)
    db.session.commit()
    exercs = Exercise.query.filter_by(name='bench press').first()

    workout = Workout(
        date=datetime.now().date(),
        sets=3,
        reps=[10, 10, 10],
        extra_weight=[0, 0, 0],
        is_bodyweight=False,
        exercise_id=exercs.id,
        user_id=usr.id
    )
    existingWorkout = Workout.query.filter_by(
        date=workout.date, sets=workout.sets, reps=workout.reps, extra_weight=workout.extra_weight,
        is_bodyweight=workout.is_bodyweight, exercise_id=workout.exercise_id, user_id=workout.user_id).first()
    if not existingWorkout:
        db.session.add(workout)
    db.session.commit()


# Helpers


def getWorkoutsByDate(date, userid):
    return Workout.query.filter_by(date=date, user_id=userid).all()


def getDaysOfWorkoutInMonth(month, year, userid):
    first_day_of_month = datetime(year, month, 1)
    days_in_month = calendar.monthrange(year, month)[1]
    workouts = Workout.query.filter(
        Workout.date.between(first_day_of_month, datetime(
            year, month, days_in_month)),
        Workout.user_id == userid
    ).all()
    workout_days = {workout.date.day for workout in workouts}
    print(sorted(workout_days))
    return sorted(workout_days)


def workoutconstraintIdtoName(workout):
    workoutWithNames = workout.__dict__.copy()
    workoutWithNames['user_id'] = User.query.filter_by(
        id=workout.user_id).first().username
    workoutWithNames['exercise_id'] = Exercise.query.filter_by(
        id=workout.exercise_id).first().name
    return workoutWithNames


def getExerciseIdByName(name, userid):
    exercise = Exercise.query.filter_by(name=name, user_id=userid).first()
    if exercise:
        return exercise.id
    return None


def getWorkoutsByExercise(exercise, userid):
    return Workout.query.filter_by(exercise_id=exercise.id, user_id=userid).all()


def getWorkoutsByExerciseName(exercisename, userid):
    exercise = Exercise.query.filter_by(
        name=exercisename, user_id=userid).first()
    if exercise:
        return Workout.query.filter_by(exercise_id=exercise.id, user_id=userid).all()
    return []


def getAllWorkouts(userid):
    return Workout.query.filter_by(user_id=userid).all()


def getExercises(userid):
    exercises = Exercise.query.filter_by(user_id=userid).all()
    return [exercise.to_dict() for exercise in exercises]


def addExercise(exerciseName, userid):
    existingExercise = Exercise.query.filter_by(
        name=exerciseName, user_id=userid).first()
    if not existingExercise:
        newExercise = Exercise(name=exerciseName, user_id=userid)
        db.session.add(newExercise)
        db.session.commit()
    return Exercise.query.filter_by(name=exerciseName, user_id=userid).first()


def getExerciseById(exerciseId, userid):
    return Exercise.query.filter_by(id=exerciseId, user_id=userid).first()


def addWorkout(workout):
    existingWorkout = Workout.query.filter_by(
        date=workout.date,
        sets=workout.sets,
        reps=workout.reps,
        extra_weight=workout.extra_weight,
        is_bodyweight=workout.is_bodyweight,
        exercise_id=workout.exercise_id,
        user_id=workout.user_id,
    ).first()
    if not existingWorkout:
        db.session.add(workout)
        db.session.commit()
    return Workout.query.filter_by(
        date=workout.date,
        sets=workout.sets,
        reps=workout.reps,
        extra_weight=workout.extra_weight,
        is_bodyweight=workout.is_bodyweight,
        exercise_id=workout.exercise_id,
        user_id=workout.user_id,
    ).first()


def addUser(username, passwordHash):
    existingUser = User.query.filter_by(username=username).first()
    if not existingUser:
        newUser = User(username=username, passwordHash=passwordHash)
        db.session.add(newUser)
        db.session.commit()

    return User.query.filter_by(username=username).first()


def getUser(username):
    return User.query.filter_by(username=username).first()


def seedExercises(userid):
    exercises = [
        Exercise(name='bench press', user_id=userid),
        Exercise(name='squat', user_id=userid),
        Exercise(name='deadlift', user_id=userid),
        Exercise(name='pull-ups', user_id=userid),
        Exercise(name='push-ups', user_id=userid),
        Exercise(name='skull crushers', user_id=userid)
    ]

    with db.session.no_autoflush:
        # Filter out existing exercises from the list before adding
        exercises_to_add = [ex for ex in exercises if not Exercise.query.filter_by(
            name=ex.name, user_id=ex.user_id).first()]

        # Add the remaining exercises
        db.session.add_all(exercises_to_add)

    db.session.commit()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.2, min=0.2, max=2),
    retry=retry_if_exception_type((requests.RequestException, UpstreamError)),
    reraise=True
)
def _do_stats_get(path, params=None) -> requests.Response:
    url = f"{STATS_SERVICE_URL}{path}"
    r = requests.get(url, params=params, timeout=2.5)
    # 5xx == failure (triggers retry / breaker)
    if r.status_code >= 500:
        raise UpstreamError(f"Upstream returned {r.status_code}")
    return r


def stats_get_with_breaker(path, params=None, fallback=None):
    # wrapper that applies circuit breaker / retry
    try:
        # breaker wraps the retried call
        r = stats_breaker.call(_do_stats_get, path, params)
        # forward JSON if possible
        try:
            return r.json(), r.status_code
        except Exception:
            return {"status": "ERROR", "error": "Upstream returned non-JSON"}, 502

    except pybreaker.CircuitBreakerError:
        # breaker OPEN
        return (fallback or {"status": "DEGRADED", "error": "stats-service unavailable (circuit open)"}), 503

    except Exception as e:
        # maxed retries or hard failure
        return (fallback or {"status": "DEGRADED", "error": f"stats-service unavailable ({type(e).__name__})"}), 503

# Routes


@app.get("/resilience")
def resilience_status():
    """
    Resilience status for stats-service proxy (circuit breaker state).
    ---
    tags:
      - Resilience
    responses:
      200:
        description: Current circuit breaker state and counters
        schema:
          type: object
          properties:
            breaker_state: {type: string, example: "closed"}
            fail_counter: {type: integer, example: 0}
            stats_service_url: {type: string, example: "http://stats:5000"}
    """
    return jsonify({
        "breaker_state": str(stats_breaker.current_state),
        "fail_counter": stats_breaker.fail_counter,
        "stats_service_url": STATS_SERVICE_URL
    }), 200


@app.get("/api/time")
def api_time():
    """
    Get server time for configured timezone (proxy to stats-service external API).
    ---
    tags:
      - External
    responses:
      200:
        description: Time info
        schema:
          type: object
          properties:
            timezone: {type: string, example: "Europe/Ljubljana"}
            formatted: {type: string, example: "2026-01-10 02:34:40"}
            source: {type: string, example: "timezonedb"}
      503:
        description: Degraded mode (stats-service unavailable or circuit open)
        schema:
          type: object
          properties:
            status: {type: string, example: "DEGRADED"}
            error: {type: string, example: "stats-service unavailable (circuit open)"}
    """
    payload, code = stats_get_with_breaker(
        "/external/time",
        fallback={
            "status": "DEGRADED",
            "error": "Time service unavailable",
            "source": "fallback",
            "timezone": os.getenv("DEFAULT_TZ", "Europe/Ljubljana")
        }
    )
    return jsonify(payload), code


@app.route("/statsSummary", methods=["GET"])
def stats_summary():
    """
    Stats summary for logged-in user (proxy to stats-service).
    ---
    tags:
      - Proxy
    responses:
      200:
        description: Summary stats for the authenticated user
      302:
        description: Redirect to login if not authenticated
      503:
        description: Degraded mode (stats-service unavailable or circuit open)
        schema:
          type: object
          properties:
            status: {type: string, example: "DEGRADED"}
            error: {type: string, example: "Stats service is unavailable"}
            source: {type: string, example: "fallback"}
    """
    if "uid" not in session:
        return redirect(url_for("loginScreen"))

    payload, code = stats_get_with_breaker(
        "/stats/summary",
        params={"user_id": session["uid"]},
        fallback={
            "status": "DEGRADED",
            "error": "Stats service is unavailable",
            "user_id": session["uid"],
            "total_workouts": 0,
            "total_sets": 0,
            "total_reps": 0,
            "total_tonnage": 0.0,
            "source": "fallback"
        }
    )
    return jsonify(payload), code


@app.route("/health")
def health():
    """
    Health check for core service.
    ---
    tags:
      - Health
    responses:
      200:
        description: Service is up
        schema:
          type: object
          properties:
            status: {type: string, example: UP}
    """
    return jsonify({"status": "UP"}), 200


@app.route('/calendar', methods=['GET'])
def calendar_redirect():
    if 'uid' not in session:
        return redirect(url_for('loginScreen'))
    current_year = datetime.now().year
    current_month = datetime.now().month
    return redirect(url_for('calendar_page', year=current_year, month=current_month))


@app.route('/calendarDefault', methods=['GET'])
def calendarDefault():
    return calendar_redirect()


@app.route('/calendar/<int:year>/<int:month>', methods=['GET'])
def calendar_page(year, month):
    if 'uid' not in session:
        return redirect(url_for('loginScreen'))
    if (month < 1):
        return redirect(url_for('calendar_page', year=year-1, month=12))
    if (month > 12):
        return redirect(url_for('calendar_page', year=year+1, month=1))
    current_year = int(year)
    current_month = int(month)

    first_day_of_month = datetime(current_year, current_month, 1)
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    month_days = calendar.monthcalendar(current_year, current_month)
    workouts = Workout.query.filter(Workout.date.between(
        first_day_of_month, datetime(current_year, current_month, days_in_month))).all()

    # TODO
    workouts_by_date = {}
    for workout in workouts:
        workouts_by_date.setdefault(workout.date, []).append(workout)

    return render_template('calendar.html', current_year=current_year, current_month=current_month, month_days=month_days, workouts_by_date=workouts_by_date)


@app.route('/addExercise', methods=['POST'])
def add_exercise():
    """
    Add a new exercise for the logged-in user.
    ---
    tags:
      - Core
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name: {type: string, example: "bench press"}
    responses:
      200:
        description: Exercise created
        schema:
          type: object
          properties:
            success: {type: boolean, example: true}
      302:
        description: Redirect to login if not authenticated
    """
    if 'uid' not in session:
        return redirect(url_for('loginScreen'))
    data = request.get_json()
    exerciseName = data.get('name')
    if exerciseName:
        exercise = Exercise(name=exerciseName, user_id=session['uid'])
        db.session.add(exercise)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})


# @app.route('/getAllExercises', methods=['GET'])
# def getAllExercises():
#     exercises = getExercises(session['uid'])
#     return jsonify(exercises)

# proxy for the other microservice
@app.route('/getAllExercises', methods=['GET'])
def getAllExercises():
    """
    Get all exercises for the logged-in user (proxy to stats-service).
    ---
    tags:
      - Proxy
    responses:
      200:
        description: List of exercises
        schema:
          type: array
          items:
            type: object
            properties:
              id: {type: integer, example: 1}
              name: {type: string, example: "bench press"}
              user_id: {type: integer, example: 1}
      302:
        description: Redirect to login if user not authenticated
      503:
        description: Degraded mode (stats-service unavailable or circuit open)
    """
    if 'uid' not in session:
        return redirect(url_for('loginScreen'))

    payload, code = stats_get_with_breaker(
        "/api/exercises",
        params={"user_id": session["uid"]},
        fallback={"status": "DEGRADED",
                  "error": "Stats service unavailable", "exercises": []}
    )

    # Your frontend expects a list
    if isinstance(payload, list):
        return jsonify(payload), code

    # fallback -> return empty list so UI doesn't break
    return jsonify([]), 200


@app.route('/getExercisesInMonth/<int:year>/<int:month>', methods=['GET'])
def getExercisesInMonth(year, month):
    days = getDaysOfWorkoutInMonth(month, year, session['uid'])
    return jsonify(days)


@app.route('/addWorkout', methods=['POST'])
def add_workout():
    """
    Add a workout for the logged-in user.
    ---
    tags:
      - Core
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            workout: {type: integer, example: 2, description: "exercise_id"}
            sets: {type: integer, example: 3}
            reps:
              type: array
              items: {type: integer}
              example: [10, 10, 10]
            weights:
              type: array
              items: {type: number}
              example: [60, 60, 60]
            isbodyweight: {type: boolean, example: false}
    responses:
      200:
        description: Workout added
        schema:
          type: object
          properties:
            message: {type: string, example: "Workout added successfully"}
      400:
        description: Invalid input
        schema:
          type: string
          example: "Invalid input"
      302:
        description: Redirect to login if not authenticated
    """
    if 'uid' not in session:
        return redirect(url_for('loginScreen'))
    data = request.get_json()

    workout = data.get('workout')
    sets = data.get('sets')
    reps = data.get('reps', [])
    weights = data.get('weights', [])
    is_bodyweight = data.get('isbodyweight', False)

    if not workout or sets is None or not reps or not weights:
        return "Invalid input", 400

    print(
        f"Workout: {workout}, Sets: {sets}, Reps: {reps}, Weights: {weights}, Is Bodyweight: {is_bodyweight}")

    #  exercise id, userid

    newWorkout = Workout(
        date=datetime.now(),
        sets=sets,
        reps=reps,
        extra_weight=weights,
        is_bodyweight=is_bodyweight,
        exercise_id=workout,
        user_id=session['uid']
    )
    addWorkout(newWorkout)

    return jsonify({"message": "Workout added successfully"}), 200


@app.route('/workout', methods=['GET', 'POST'])
def workout():
    if 'uid' not in session:
        return redirect(url_for('loginScreen'))
    if request.method == 'POST':
        # Handle form submission, saving workout data, etc.
        name = request.form['name']
        sets = request.form['sets']
        reps = request.form['reps']
        extra_weight = request.form['extra_weight']
        is_bodyweight = request.form.get('is_bodyweight') == 'on'
        date = request.form['date']

        return redirect(url_for('calendar_page'))
    else:
        return render_template('workout.html', exercises=getExercises(session['uid']))


@app.route('/workouts/<date>', methods=['GET'])
def workouts(date):
    if 'uid' not in session:
        return redirect(url_for('loginScreen'))
    selected_date = datetime.strptime(
        date, '%Y-%m-%d').date().strftime('%d %B %Y')
    workouts = getWorkoutsByDate(date, session['uid'])
    return render_template('workoutsInCalendar.html', workouts=workouts, date=selected_date, userid=session['uid'], getExerciseById=getExerciseById)


@app.route('/', methods=['GET'])
def loginScreen():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    action = request.form.get('action')

    if not username or not password:
        flash("Username and Password are required.", "error")
        return redirect(url_for('loginScreen'))

    if action == 'login':
        user = getUser(username)
        if user:
            if bcrypt.checkpw(password.encode('utf-8'), user.passwordHash.encode('utf-8')):
                session['uid'] = user.id
                session['username'] = user.username
                flash("Login successful!", "success")
                return redirect(url_for('workout'))
            else:
                flash("Invalid username or password.", "error")
        else:
            flash("User not found.", "error")

    elif action == 'register':
        user = getUser(username)
        if user:
            flash("User already exists.", "error")
        else:
            passwordHash = bcrypt.hashpw(password.encode(
                'utf-8'), bcrypt.gensalt()).decode('utf-8')
            newUserid = addUser(username, passwordHash).id
            seedExercises(newUserid)
            flash("User registered successfully!", "success")
            return redirect(url_for('loginScreen'))

    return redirect(url_for('loginScreen'))


@app.route('/logout')
def logout():
    session.pop('uid', None)
    session.pop('username', None)
    session.pop('_flashes', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('loginScreen'))

####################################################################################
####################################################################################
######################### ZA IZRIS GRAFOV ##########################################
####################################################################################
####################################################################################


@app.route('/stats')
def show_stats():
    if 'uid' not in session:
        return redirect(url_for('loginScreen'))
    return render_template('stats.html')


# @app.route('/getAllWorkoutsForUser', methods=['GET'])
# def getAllWorkoutsForUser():
#     # Assuming getAllWorkouts is a function that fetches workouts
#     workouts = getAllWorkouts(session['uid'])
#     # Convert each Workout object to a dictionary
#     workouts_serializable = [workout.to_dict() for workout in workouts]
#     return jsonify(workouts_serializable)

# proxy for the other microservice
@app.route('/getAllWorkoutsForUser', methods=['GET'])
def getAllWorkoutsForUser():
    """
    Get all workouts for the logged-in user (proxy to stats-service).
    ---
    tags:
      - Proxy
    responses:
      200:
        description: List of workouts for authenticated user
      302:
        description: Redirect to login if not authenticated
      503:
        description: Degraded mode (stats-service unavailable or circuit open)
    """
    if 'uid' not in session:
        return redirect(url_for('loginScreen'))

    payload, code = stats_get_with_breaker(
        "/api/workouts",
        params={"user_id": session["uid"]},
        fallback={"status": "DEGRADED",
                  "error": "Stats service unavailable", "workouts": []}
    )

    if isinstance(payload, list):
        return jsonify(payload), code

    # fallback -> keep frontend stable
    return jsonify([]), 200


if __name__ == '__main__':
    # with app.app_context():
    #     db.create_all()
    # seedDB()
    app.run(host='0.0.0.0', port=25590, debug=True)
