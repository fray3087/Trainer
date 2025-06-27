import random

class AIPersonalTrainer:
    def __init__(self, user_profile, previous_workouts=None):
        self.user_profile = user_profile
        self.previous_workouts = previous_workouts if previous_workouts else []
        self.exercise_database = self._load_exercise_database()

    def _load_exercise_database(self):
        # In a real application, this would come from a database or a more extensive config file
        return {
            'chest': ['Bench Press', 'Incline Dumbbell Press', 'Dumbbell Flyes', 'Push-ups', 'Cable Crossovers'],
            'back': ['Pull-ups', 'Bent-over Rows', 'Seated Cable Rows', 'Lat Pulldowns', 'Deadlifts (Conventional/Sumo)'],
            'legs': ['Squats', 'Leg Press', 'Romanian Deadlifts', 'Lunges', 'Hamstring Curls', 'Calf Raises'],
            'shoulders': ['Overhead Press', 'Lateral Raises', 'Front Raises', 'Reverse Pec Deck', 'Arnold Press'],
            'biceps': ['Barbell Curls', 'Dumbbell Curls', 'Hammer Curls', 'Concentration Curls'],
            'triceps': ['Close-grip Bench Press', 'Overhead Dumbbell Extension', 'Tricep Pushdowns', 'Skullcrushers'],
            'core': ['Plank', 'Crunches', 'Leg Raises', 'Russian Twists', 'Cable Woodchoppers']
        }

    def _get_exercises_for_muscle_group(self, muscle_group, count=1, excluded_exercises=None):
        if excluded_exercises is None:
            excluded_exercises = []

        available_exercises = [ex for ex in self.exercise_database.get(muscle_group, []) if ex not in excluded_exercises]
        if not available_exercises:
            return [] # Or handle this case by suggesting alternatives from a broader category

        return random.sample(available_exercises, min(count, len(available_exercises)))

    def create_workout_program(self, days_per_week, goal, experience_level, disliked_exercises=None):
        if disliked_exercises is None:
            disliked_exercises = []

        program = []
        # Basic split examples, can be much more sophisticated
        if days_per_week == 1: # Full Body
            split = [{'name': 'Full Body', 'muscles': ['chest', 'back', 'legs', 'shoulders', 'core']}]
        elif days_per_week == 2: # Upper/Lower
            split = [
                {'name': 'Upper Body A', 'muscles': ['chest', 'back', 'shoulders', 'biceps', 'triceps']},
                {'name': 'Lower Body A', 'muscles': ['legs', 'core']}
            ]
        elif days_per_week == 3: # Full Body or PPL variation
            split = [
                {'name': 'Full Body A', 'muscles': ['chest', 'back', 'legs']},
                {'name': 'Full Body B (Focus Shoulders/Arms)', 'muscles': ['shoulders', 'biceps', 'triceps', 'core']},
                {'name': 'Full Body C (Focus Legs/Back)', 'muscles': ['legs', 'back', 'chest']}
            ]
        elif days_per_week == 4: # Upper/Lower
            split = [
                {'name': 'Upper Body A', 'muscles': ['chest', 'back', 'shoulders']},
                {'name': 'Lower Body A', 'muscles': ['legs', 'core']},
                {'name': 'Upper Body B', 'muscles': ['shoulders', 'biceps', 'triceps']}, # Different focus
                {'name': 'Lower Body B', 'muscles': ['legs', 'back']} # e.g. Deadlift focus
            ]
        elif days_per_week >= 5: # PPL (Push, Pull, Legs) or Body Part Split
            split = [
                {'name': 'Push Day (Chest, Shoulders, Triceps)', 'muscles': ['chest', 'shoulders', 'triceps']},
                {'name': 'Pull Day (Back, Biceps)', 'muscles': ['back', 'biceps']},
                {'name': 'Leg Day', 'muscles': ['legs', 'core']},
                {'name': 'Push Day 2 (Variation)', 'muscles': ['chest', 'shoulders', 'triceps']},
                {'name': 'Pull Day 2 (Variation)', 'muscles': ['back', 'biceps']},
                # Could add a 6th day for Legs or Full Body light day
            ]
            if days_per_week == 6:
                split.append({'name': 'Leg Day 2 or Accessory', 'muscles': ['legs', 'core']}) # Example
        else:
            return "Invalid number of training days."

        for day_info in split[:days_per_week]:
            workout_day = {'day_name': day_info['name'], 'exercises': []}
            num_exercises_per_muscle = 2 if experience_level in ['intermediate', 'advanced'] else 1
            if goal == 'strength':
                num_exercises_per_muscle = 1 # Focus on compounds

            for muscle in day_info['muscles']:
                # Adjust exercise count based on muscle group size / importance for the day
                exercise_count = num_exercises_per_muscle
                if muscle in ['legs', 'back', 'chest'] and experience_level != 'beginner':
                    exercise_count = min(3, num_exercises_per_muscle +1) # More for larger groups
                if muscle == 'core' and experience_level == 'beginner':
                     exercise_count = 1
                elif muscle == 'core':
                    exercise_count = 2


                selected_exercises = self._get_exercises_for_muscle_group(muscle, exercise_count, disliked_exercises)
                for ex_name in selected_exercises:
                    sets, reps, rir, rest_period = self._get_set_rep_scheme(ex_name, goal, experience_level)
                    workout_day['exercises'].append({
                        'name': ex_name,
                        'sets': sets,
                        'reps': reps,
                        'rir': rir, # Reps In Reserve
                        'rest_period_seconds': rest_period,
                        'notes': f"Focus on {goal}. Maintain good form."
                    })
            program.append(workout_day)
        return program

    def _get_set_rep_scheme(self, exercise_name, goal, experience_level):
        # Default values
        sets, reps, rir, rest = 3, "8-12", 2, 60

        # Goal-based adjustments
        if goal == 'muscle_gain': # Hypertrophy
            sets = 3 if experience_level == 'beginner' else 4
            reps = "8-12" if "Press" in exercise_name or "Squat" in exercise_name or "Deadlift" in exercise_name else "10-15"
            rir = 2 if experience_level != 'advanced' else 1 # Could go closer to failure for advanced
            rest = 60 if "iso" in exercise_name.lower() else 90 # Shorter for isolation, longer for compounds
        elif goal == 'strength':
            sets = 3 if experience_level == 'beginner' else 5
            reps = "3-6" if "Press" in exercise_name or "Squat" in exercise_name or "Deadlift" in exercise_name else "6-8"
            rir = 1 # Closer to failure or actual failure for some sets
            rest = 120 if experience_level != 'beginner' else 90
        elif goal == 'endurance':
            sets = 2 if experience_level == 'beginner' else 3
            reps = "15-20+"
            rir = 3 # Further from failure
            rest = 30

        # Experience-level adjustments (can refine these)
        if experience_level == 'beginner':
            sets = min(sets, 3) # Cap sets for beginners
            rir = max(rir, 2) # More reps in reserve for beginners
        elif experience_level == 'advanced':
            # Advanced users might use more complex periodization, this is simplified
            if goal == 'muscle_gain':
                 rir = random.choice([0,1,2]) # Vary RIR for advanced
            elif goal == 'strength':
                 rir = random.choice([0,1])


        # Technique suggestions (can be expanded)
        if experience_level == 'advanced' and goal == 'muscle_gain' and random.random() < 0.2: # 20% chance for advanced technique
            technique = random.choice(['dropset', 'restpause'])
            if technique == 'dropset':
                return sets, reps, rir, rest, "Consider a dropset on the final set."
            elif technique == 'restpause':
                 return sets, reps, rir, rest, "Consider rest-pause on the final set for max effort."

        return sets, reps, rir, rest, None # No special technique note

    def suggest_progression(self, last_workout_log_for_exercise):
        """
        Suggests progression based on the last performance of a specific exercise.
        Requires a log entry with 'exercise_name', 'sets', 'reps_completed', 'weight_lifted', 'rir_achieved'.
        """
        if not last_workout_log_for_exercise:
            return "No previous data for this exercise. Start with a baseline."

        name = last_workout_log_for_exercise.get('exercise_name')
        sets = last_workout_log_for_exercise.get('sets_completed', 3) # default if not logged
        reps_achieved_str = str(last_workout_log_for_exercise.get('reps_achieved', "8")) # default
        weight = last_workout_log_for_exercise.get('weight_lifted', 50) # default
        rir_achieved = last_workout_log_for_exercise.get('rir_achieved', 2) # default

        # Try to parse reps achieved, could be a range like "8-10" or a single number
        try:
            if '-' in reps_achieved_str:
                reps_achieved_list = [int(r.strip()) for r in reps_achieved_str.split('-')]
                avg_reps_achieved = sum(reps_achieved_list) / len(reps_achieved_list)
            else:
                avg_reps_achieved = int(reps_achieved_str)
        except ValueError:
            avg_reps_achieved = 8 # Fallback if parsing fails

        # Progression logic (simplified)
        # Priority: 1. Reps, 2. Weight, 3. Sets (less frequent)

        # If RIR was high (easy), increase reps or weight
        if rir_achieved >= 3: # Could also be if target reps were easily met
            if avg_reps_achieved < 12 : # Assuming a hypertrophy target range of 8-12 for this example
                 return f"For {name}: Good job! Try to increase reps to {int(avg_reps_achieved + 1)}-{int(avg_reps_achieved + 2)} at {weight}kg. Or, if form is solid, increase weight slightly."
            else: # Maxed out reps in target range
                return f"For {name}: Great! Increase weight by 2.5-5kg and aim for the lower end of your rep target (e.g., 8 reps)."

        # If RIR was low (challenging but good), maintain or small increment
        elif rir_achieved in [1, 2]:
            if avg_reps_achieved < 10: # Still room in rep range
                 return f"For {name}: Solid effort! Aim for {int(avg_reps_achieved + 1)} reps at {weight}kg. Focus on form."
            else: # Good reps, consider weight
                 return f"For {name}: Well done! Maintain {weight}kg and try to hit the higher end of your rep range, or consider a small weight increase if RIR was 2."

        # If RIR was 0 or failed (too hard)
        else: # rir_achieved == 0 or lower (failure)
            return f"For {name}: That was tough! Consider reducing weight by 5-10% to ensure good form and hit your target reps. Or, maintain weight and aim for slightly fewer reps with perfect form."

        return f"For {name}: Maintain current load/reps and focus on technique. Or try a different progression strategy."

    def get_alternative_exercise(self, disliked_exercise_name, muscle_group_of_disliked):
        alternatives = self._get_exercises_for_muscle_group(muscle_group_of_disliked, count=2, excluded_exercises=[disliked_exercise_name])
        if alternatives:
            return f"Instead of {disliked_exercise_name}, you could try: {', '.join(alternatives)}."
        return f"No direct alternative found for {disliked_exercise_name} in the same muscle group. Consider other exercises for {muscle_group_of_disliked} or a different movement pattern."

# Example Usage (for testing purposes)
if __name__ == '__main__':
    # Mock user profile
    user_data = {
        'username': 'TestUser',
        'goal': 'muscle_gain', # 'strength', 'endurance'
        'training_frequency_preference': 4, # days per week
        'training_level': 'intermediate', # 'beginner', 'advanced'
        'disliked_exercises': ['Squats'] # Example
    }

    ai_coach = AIPersonalTrainer(user_profile=user_data)

    # Create a workout program
    program = ai_coach.create_workout_program(
        days_per_week=user_data['training_frequency_preference'],
        goal=user_data['goal'],
        experience_level=user_data['training_level'],
        disliked_exercises=user_data['disliked_exercises']
    )

    print("--- Generated Workout Program ---")
    if isinstance(program, str):
        print(program)
    else:
        for i, day_workout in enumerate(program):
            print(f"\nDay {i+1}: {day_workout['day_name']}")
            for exercise in day_workout['exercises']:
                print(f"  - {exercise['name']}: {exercise['sets']} sets of {exercise['reps']} reps, RIR {exercise['rir']}, Rest: {exercise['rest_period_seconds']}s")
                if 'notes_technique' in exercise:
                    print(f"    Note: {exercise['notes_technique']}")

    print("\n--- Exercise Alternative Example ---")
    alternative = ai_coach.get_alternative_exercise("Squats", "legs")
    print(alternative)
    alternative_bp = ai_coach.get_alternative_exercise("Bench Press", "chest")
    print(alternative_bp)


    print("\n--- Progression Suggestion Example ---")
    # Mock previous workout log for a specific exercise
    last_bench_press_log = {
        'exercise_name': 'Bench Press',
        'sets_completed': 3,
        'reps_achieved': '8-8-7', # Example of how reps might be logged
        'weight_lifted': 80, # kg
        'rir_achieved': 2
    }
    progression_suggestion = ai_coach.suggest_progression(last_bench_press_log)
    print(progression_suggestion)

    last_squat_log_fail = {
        'exercise_name': 'Leg Press', # User dislikes squats, so logs leg press
        'sets_completed': 3,
        'reps_achieved': '6-5-4',
        'weight_lifted': 120,
        'rir_achieved': 0
    }
    progression_suggestion_fail = ai_coach.suggest_progression(last_squat_log_fail)
    print(progression_suggestion_fail)

    last_curl_log_easy = {
        'exercise_name': 'Bicep Curls',
        'sets_completed': 3,
        'reps_achieved': '15-15-15',
        'weight_lifted': 10,
        'rir_achieved': 4
    }
    progression_suggestion_easy = ai_coach.suggest_progression(last_curl_log_easy)
    print(progression_suggestion_easy)
