from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import sha256_crypt
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness_app.db'
app.config['SECRET_KEY'] = os.urandom(24)
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    goal = db.Column(db.String(120))
    training_frequency = db.Column(db.String(120))
    training_level = db.Column(db.String(120))

class WorkoutProgram(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    user = db.relationship('User', backref=db.backref('workout_programs', lazy=True))

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    muscle_group = db.Column(db.String(120))

class WorkoutLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('workout_program.id'))
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'))
    date = db.Column(db.DateTime, server_default=db.func.now())
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight = db.Column(db.Float)
    rir = db.Column(db.Integer) # Reps in Reserve
    notes = db.Column(db.Text)
    user = db.relationship('User', backref=db.backref('workout_logs', lazy=True))
    program = db.relationship('WorkoutProgram', backref=db.backref('logs', lazy=True))
    exercise = db.relationship('Exercise', backref=db.backref('logs', lazy=True))

# --- Authentication Routes ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not username or not password or not email:
        return jsonify({'message': 'Missing username, password, or email'}), 400

    if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
        return jsonify({'message': 'Username or email already exists'}), 409

    hashed_password = sha256_crypt.hash(password)
    new_user = User(username=username, password=hashed_password, email=email)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and sha256_crypt.verify(password, user.password):
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({'message': 'Login successful', 'user_id': user.id, 'username': user.username}), 200
    else:
        return jsonify({'message': 'Invalid username or password'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/api/check_session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'user_id': session['user_id'], 'username': session['username']}), 200
    return jsonify({'logged_in': False}), 200

# --- User Profile Route ---
@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    if 'user_id' not in session or session['user_id'] != user_id:
        return jsonify({'message': 'Unauthorized'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'goal': user.goal,
        'training_frequency': user.training_frequency,
        'training_level': user.training_level
        # Add other fields as needed, but be careful about exposing sensitive data
    }), 200

@app.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user_profile(user_id):
    if 'user_id' not in session or session['user_id'] != user_id:
        return jsonify({'message': 'Unauthorized'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = request.get_json()
    user.goal = data.get('goal', user.goal)
    user.training_frequency = data.get('training_frequency', user.training_frequency)
    user.training_level = data.get('training_level', user.training_level)
    # Add other updatable fields here

    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'}), 200

# --- AI Trainer Routes ---
from ai_trainer import AIPersonalTrainer

@app.route('/api/ai/generate_program', methods=['POST'])
def generate_program():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized - Please log in'}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = request.get_json()
    days_per_week = data.get('days_per_week', user.training_frequency) # Default to profile if not provided
    goal = data.get('goal', user.goal)
    experience_level = data.get('experience_level', user.training_level)
    disliked_exercises = data.get('disliked_exercises', []) # Comes from frontend input potentially

    if not all([days_per_week, goal, experience_level]):
        return jsonify({'message': 'Missing required parameters: days_per_week, goal, experience_level'}), 400

    try:
        # Convert days_per_week from string like "3 times a week" to integer
        if isinstance(days_per_week, str):
            days_per_week = int(days_per_week.split()[0])
    except ValueError:
        return jsonify({'message': 'Invalid format for days_per_week. Expected integer or string like "3 times a week".'}), 400


    user_profile_for_ai = {
        'username': user.username,
        'goal': goal,
        'training_frequency_preference': days_per_week,
        'training_level': experience_level,
        'disliked_exercises': disliked_exercises
    }
    # TODO: Fetch previous workouts for this user to pass to the AI trainer for better personalization
    # previous_workouts_db = WorkoutLog.query.filter_by(user_id=user.id).order_by(WorkoutLog.date.desc()).limit(20).all()
    # previous_workouts_formatted = [...] # Format these logs as needed by AI

    parsed_days_per_week = 0
    if isinstance(days_per_week, str):
        try:
            # Attempt to get the first part and convert to int, e.g., "3 times a week" -> 3
            parsed_days_per_week = int(days_per_week.split()[0])
        except (ValueError, IndexError):
            return jsonify({'message': 'Invalid format for days_per_week string. Expected format like "3 times a week".'}), 400
    elif isinstance(days_per_week, int):
        parsed_days_per_week = days_per_week
    else:
        return jsonify({'message': 'days_per_week must be an integer or a string like "3 times a week".'}), 400

    if parsed_days_per_week <= 0:
        return jsonify({'message': 'days_per_week must be a positive number.'}), 400

    user_profile_for_ai['training_frequency_preference'] = parsed_days_per_week # Update profile for AI with parsed int

    ai_coach = AIPersonalTrainer(user_profile=user_profile_for_ai, previous_workouts=[]) # Pass empty for now

    workout_program_generated = ai_coach.create_workout_program(
        days_per_week=parsed_days_per_week, # Use parsed integer
        goal=goal,
        experience_level=experience_level,
        disliked_exercises=disliked_exercises
    )

    if isinstance(workout_program_generated, str): # AI returned an error message
        return jsonify({'message': workout_program_generated}), 400

    # Save the generated program to the WorkoutProgram table
    program_name = f"AI: {goal.capitalize()} - {parsed_days_per_week} days ({experience_level})"
    program_description = (f"AI generated program for {user.username}. "
                           f"Focus: {goal}, Level: {experience_level}, Days: {parsed_days_per_week}. "
                           f"Program Details: {str(workout_program_generated)}") # Store JSON as string for now

    new_program_db = WorkoutProgram(user_id=user.id, name=program_name, description=program_description)
    db.session.add(new_program_db)

    try:
        db.session.commit()
        return jsonify({
            'message': 'Workout program generated and saved successfully',
            'program': workout_program_generated,
            'program_id': new_program_db.id
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error saving generated program: {e}")
        # Return the program even if save fails, but with a different message
        return jsonify({
            'message': 'Workout program generated but failed to save to database. Please try saving manually.',
            'program': workout_program_generated
        }), 500


@app.route('/api/ai/suggest_progression', methods=['POST'])
def suggest_exercise_progression():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized'}), 401

    data = request.get_json()
    last_workout_log_for_exercise = data.get('last_workout_log') # Expects a dict matching AI input

    if not last_workout_log_for_exercise:
        return jsonify({'message': 'Missing last_workout_log data'}), 400

    user = User.query.get(session['user_id']) # For context if needed by AI
    ai_coach = AIPersonalTrainer(user_profile={'training_level': user.training_level if user else 'intermediate'}) # Simplified profile for this

    suggestion = ai_coach.suggest_progression(last_workout_log_for_exercise)
    return jsonify({'suggestion': suggestion}), 200

@app.route('/api/ai/alternative_exercise', methods=['POST'])
def get_alternative_exercise_api():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized'}), 401

    data = request.get_json()
    disliked_exercise = data.get('disliked_exercise')
    muscle_group = data.get('muscle_group')

    if not disliked_exercise or not muscle_group:
        return jsonify({'message': 'Missing disliked_exercise or muscle_group'}), 400

    ai_coach = AIPersonalTrainer(user_profile={}) # No specific profile needed for this basic version
    alternative = ai_coach.get_alternative_exercise(disliked_exercise, muscle_group)
    return jsonify({'alternative': alternative}), 200

# --- Workout Logging and Summary Routes ---
@app.route('/api/log_workout', methods=['POST'])
def log_workout_api():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized'}), 401

    data = request.get_json()
    user_id = session['user_id']
    workout_name = data.get('workout_name', 'General Workout') # Name of the overall workout session
    exercises_logged = data.get('exercises') # This should be a list of exercise logs

    if not exercises_logged or not isinstance(exercises_logged, list):
        return jsonify({'message': 'No exercises provided or in wrong format'}), 400

    # Optional: Find or create a WorkoutProgram entry for this session
    # For now, we'll log exercises directly. A more robust system would link these logs to a specific program instance.
    # program_entry = WorkoutProgram.query.filter_by(user_id=user_id, name=workout_name).first()
    # if not program_entry:
    #     program_entry = WorkoutProgram(user_id=user_id, name=workout_name, description="Logged workout session")
    #     db.session.add(program_entry)
    #     db.session.commit() # Get program_entry.id if needed for WorkoutLog

    for ex_log in exercises_logged:
        exercise_name = ex_log.get('exercise_name')
        exercise_entry = Exercise.query.filter_by(name=exercise_name).first()
        if not exercise_entry:
            # Optionally create new exercises if they don't exist, or restrict to existing ones
            # For now, we'll skip if not found, or you can create it:
            # exercise_entry = Exercise(name=exercise_name, description="User logged exercise")
            # db.session.add(exercise_entry)
            # db.session.commit()
            # print(f"Exercise '{exercise_name}' not found in DB, skipping or auto-adding.")
            return jsonify({'message': f"Exercise '{exercise_name}' not found. Please ensure it exists in the database or add it first."}), 400


        new_log = WorkoutLog(
            user_id=user_id,
            # program_id=program_entry.id if program_entry else None, # Assuming program_id might be added later
            exercise_id=exercise_entry.id,
            sets=ex_log.get('sets_completed'),
            reps=str(ex_log.get('reps_achieved', '')), # Ensure reps are stored as string, default to empty string if not provided
            weight=ex_log.get('weight_lifted'),
            rir=ex_log.get('rir_achieved'),
            notes=ex_log.get('notes', '') # Default to empty string for notes
        )
        db.session.add(new_log)

    try:
        db.session.commit()
        return jsonify({'message': 'Workout logged successfully'}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error logging workout: {e}")
        return jsonify({'message': 'Failed to log workout due to a server error.'}), 500


@app.route('/api/workout_summary', methods=['GET'])
def get_workout_summary_api():
    if 'user_id' not in session:
        return jsonify({'message': 'Unauthorized'}), 401

    user_id = session['user_id']

    # Basic summary: total workouts, avg duration (hard to calculate without session duration), total volume
    total_workouts_count = db.session.query(WorkoutLog.program_id).filter(WorkoutLog.user_id == user_id).distinct().count()
    # For a more accurate total_workouts_count, you'd group by a session identifier or a program instance.
    # This current count might be high if program_id is not consistently used or if it counts distinct programs logged against.
    # A better way might be to count distinct dates or group logs by sessions if a session concept is added.

    # For now, let's count distinct days a workout was logged as "total workouts"
    total_workout_sessions = db.session.query(db.func.date(WorkoutLog.date)).filter(WorkoutLog.user_id == user_id).distinct().count()

    # Calculate total_volume more robustly in Python
    all_user_logs = WorkoutLog.query.filter_by(user_id=user_id).all()
    total_volume = 0
    for log in all_user_logs:
        try:
            # Try to parse the first number from the reps string (e.g., "10-12" -> 10, "8" -> 8)
            reps_string = str(log.reps).strip()
            if not reps_string: continue # Skip if reps string is empty

            reps_value = int(reps_string.split('-')[0].strip())

            if log.weight is not None and log.sets is not None:
                total_volume += float(log.weight) * reps_value * int(log.sets)
        except (ValueError, TypeError, IndexError) as e:
            print(f"Could not parse reps or calculate volume for log_id {log.id}: {log.reps}. Error: {e}")
            # Optionally, decide how to handle entries that can't be parsed (e.g., skip, count as 0, etc.)
            pass

    recent_logs_query = WorkoutLog.query.join(Exercise).outerjoin(WorkoutProgram).filter(WorkoutLog.user_id == user_id).order_by(WorkoutLog.date.desc()).limit(10)
    recent_logs = []
    for log in recent_logs_query:
        details = f"{log.sets or 'N/A'} sets, {log.reps or 'N/A'} reps"
        if log.weight is not None:
            details += f" @ {log.weight}kg"

        recent_logs.append({
            'exercise_name': log.exercise.name if log.exercise else "Unknown Exercise",
            'date': log.date.strftime('%Y-%m-%d %H:%M') if log.date else "No Date",
            'details': details,
            'program_name': log.program.name if log.program else "General Workout"
        })

    return jsonify({
        'total_workouts': total_workout_sessions,
        'avg_duration_minutes': 0, # Placeholder
        'total_volume_lifted': round(total_volume, 2),
        'recent_workout_logs': recent_logs
    }), 200


def populate_initial_exercises():
    exercises_to_add = [
        {'name': 'Bench Press', 'muscle_group': 'chest', 'description': 'Compound chest exercise.'},
        {'name': 'Incline Dumbbell Press', 'muscle_group': 'chest', 'description': 'Upper chest focus.'},
        {'name': 'Dumbbell Flyes', 'muscle_group': 'chest', 'description': 'Chest isolation.'},
        {'name': 'Push-ups', 'muscle_group': 'chest', 'description': 'Bodyweight chest exercise.'},
        {'name': 'Cable Crossovers', 'muscle_group': 'chest', 'description': 'Chest isolation with cables.'},
        {'name': 'Pull-ups', 'muscle_group': 'back', 'description': 'Compound back exercise (bodyweight).'},
        {'name': 'Bent-over Rows', 'muscle_group': 'back', 'description': 'Compound back exercise with barbell or dumbbells.'},
        {'name': 'Seated Cable Rows', 'muscle_group': 'back', 'description': 'Machine row for back thickness.'},
        {'name': 'Lat Pulldowns', 'muscle_group': 'back', 'description': 'Simulates pull-ups, targets lats.'},
        {'name': 'Deadlifts (Conventional/Sumo)', 'muscle_group': 'back', 'description': 'Full body exercise, primarily back and legs.'},
        {'name': 'Squats', 'muscle_group': 'legs', 'description': 'Compound lower body exercise.'},
        {'name': 'Leg Press', 'muscle_group': 'legs', 'description': 'Machine alternative to squats.'},
        {'name': 'Romanian Deadlifts', 'muscle_group': 'legs', 'description': 'Hamstring and glute focused deadlift variation.'},
        {'name': 'Lunges', 'muscle_group': 'legs', 'description': 'Unilateral leg exercise.'},
        {'name': 'Hamstring Curls', 'muscle_group': 'legs', 'description': 'Isolation exercise for hamstrings.'},
        {'name': 'Calf Raises', 'muscle_group': 'legs', 'description': 'Isolation for calf muscles.'},
        {'name': 'Overhead Press', 'muscle_group': 'shoulders', 'description': 'Compound shoulder exercise.'},
        {'name': 'Lateral Raises', 'muscle_group': 'shoulders', 'description': 'Isolation for medial deltoids.'},
        {'name': 'Front Raises', 'muscle_group': 'shoulders', 'description': 'Isolation for anterior deltoids.'},
        {'name': 'Reverse Pec Deck', 'muscle_group': 'shoulders', 'description': 'Isolation for rear deltoids.'},
        {'name': 'Arnold Press', 'muscle_group': 'shoulders', 'description': 'Dumbbell shoulder press variation.'},
        {'name': 'Barbell Curls', 'muscle_group': 'biceps', 'description': 'Compound bicep exercise.'},
        {'name': 'Dumbbell Curls', 'muscle_group': 'biceps', 'description': 'Bicep isolation with dumbbells.'},
        {'name': 'Hammer Curls', 'muscle_group': 'biceps', 'description': 'Targets biceps and brachialis.'},
        {'name': 'Concentration Curls', 'muscle_group': 'biceps', 'description': 'Strict bicep isolation.'},
        {'name': 'Close-grip Bench Press', 'muscle_group': 'triceps', 'description': 'Compound tricep exercise.'},
        {'name': 'Overhead Dumbbell Extension', 'muscle_group': 'triceps', 'description': 'Tricep isolation.'},
        {'name': 'Tricep Pushdowns', 'muscle_group': 'triceps', 'description': 'Cable tricep isolation.'},
        {'name': 'Skullcrushers', 'muscle_group': 'triceps', 'description': 'Lying tricep extension.'},
        {'name': 'Plank', 'muscle_group': 'core', 'description': 'Isometric core stability exercise.'},
        {'name': 'Crunches', 'muscle_group': 'core', 'description': 'Abdominal flexion exercise.'},
        {'name': 'Leg Raises', 'muscle_group': 'core', 'description': 'Targets lower abdominals.'},
        {'name': 'Russian Twists', 'muscle_group': 'core', 'description': 'Oblique focused core exercise.'},
        {'name': 'Cable Woodchoppers', 'muscle_group': 'core', 'description': 'Rotational core exercise with cables.'}
    ]
    if Exercise.query.count() == 0:
        print("Populating initial exercises...")
        for ex_data in exercises_to_add:
            exercise = Exercise(**ex_data)
            db.session.add(exercise)
        db.session.commit()
        print("Initial exercises populated.")
    else:
        print("Exercises table already populated.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        populate_initial_exercises()
    app.run(debug=True)
