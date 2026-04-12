from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response, stream_with_context
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from openai import OpenAI
import json, os
from datetime import date, timedelta

app = Flask(__name__)
app.secret_key = '2-fat-to-fit'

USERS_FILE = 'users.json'
DATA_DIR   = 'user_data'

OPENROUTER_KEY = "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"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

os.makedirs(DATA_DIR, exist_ok=True)


# ── User store ────────────────────────────────────────────────────────────────

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)


# ── Per-user data ─────────────────────────────────────────────────────────────

def user_data_path():
    safe = ''.join(c for c in session['username'] if c.isalnum() or c in ('-', '_'))
    return os.path.join(DATA_DIR, f'{safe}.json')

def empty_user_data():
    return {
        'diet':           [],
        'hydration':      {'goal': 2000, 'current': 0},
        'workouts':       [],
        'games':          [],
        'points':         0,
        'allergies':      [],
        'goals':          '',
        'schedule':       None,
        'meal_plan':      None,
        'streak':         0,
        'last_plan_date': None,
        'longest_streak': 0,
    }

def load_user_data():
    path = user_data_path()
    if os.path.exists(path):
        with open(path, 'r') as f:
            data = json.load(f)
        for key, value in empty_user_data().items():
            data.setdefault(key, value)
        return data
    return empty_user_data()

def save_user_data(data):
    with open(user_data_path(), 'w') as f:
        json.dump(data, f, indent=2)


# ── Streak helper ─────────────────────────────────────────────────────────────

def update_streak(data):
    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last      = data.get('last_plan_date')

    if last == today:
        pass
    elif last == yesterday:
        data['streak'] = data.get('streak', 0) + 1
    else:
        data['streak'] = 1

    data['last_plan_date'] = today
    if data['streak'] > data.get('longest_streak', 0):
        data['longest_streak'] = data['streak']


# ── Auth ──────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'username' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        users    = load_users()
        if username in users and check_password_hash(users[username], password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        error = 'Invalid username or password.'
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    error = success = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')
        users    = load_users()
        if not username or not password:
            error = 'Username and password are required.'
        elif len(username) < 3:
            error = 'Username must be at least 3 characters.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        elif username in users:
            error = 'That username is already taken.'
        elif password != confirm:
            error = 'Passwords do not match.'
        else:
            users[username] = generate_password_hash(password)
            save_users(users)
            success = 'Account created! You can now sign in.'
    return render_template('register.html', error=error, success=success)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    data = load_user_data()
    return render_template('dashboard.html', data=data)


# ── AI Unified Planner ────────────────────────────────────────────────────────

@app.route('/generate_plan', methods=['POST'])
@login_required
def generate_plan():
    form      = request.get_json()
    user_data = load_user_data()

    objective   = form.get('objective', 'general fitness')
    level       = form.get('level', 'intermediate')
    equipment   = form.get('equipment', 'none')
    allergies_f = form.get('allergies', '')
    calories    = form.get('calories', '2000')

    saved_allergies = user_data.get('allergies', [])
    all_allergies   = list(set(saved_allergies + [a.strip() for a in allergies_f.split(',') if a.strip()]))
    allergy_str     = ', '.join(all_allergies) if all_allergies else 'none'

    user_prompt = (
        f"User objective: {objective}. "
        f"Fitness level: {level}. "
        f"Available equipment: {equipment}. "
        f"Food allergies / intolerances: {allergy_str}. "
        f"Daily calorie target: {calories} kcal."
    )

    system_prompt = (
        "Assume you are the role of an expert / professional coach and registered sports dietitian. "
        "Help the user plan what to do, how long to do it for, and how to do it. "
        "Return ONLY a valid JSON object — no markdown, no code fences, no extra text — in this exact shape:\n"
        "{\n"
        '  "plan": [\n'
        '    {"food": "meal name", "duration": "e.g. 10 min", "description": "exactly what to eat and how much"}\n'
        "  ],\n"
        '  "warm_up": [\n'
        '    {"name": "stretch or drill name", "duration": "e.g. 60 seconds", "how": "how to perform it"}\n'
        "  ],\n"
        '  "main_workout": [\n'
        '    {"name": "exercise name", "sets": "e.g. 3", "reps": "e.g. 12 or 30 sec", "how": "coaching cue"}\n'
        "  ],\n"
        '  "cool_down": [\n'
        '    {"name": "stretch name", "duration": "e.g. 30 seconds", "how": "how to perform it"}\n'
        "  ],\n"
        '  "sources": ["source 1", "source 2"]\n'
        "}\n"
        "The 'plan' array is the full-day meal plan (breakfast through dinner + snacks), "
        "including a clearly labelled pre-workout and post-workout meal. "
        "Respect all allergies. Be specific with quantities and macros. "
        "Do not include anything outside the JSON object."
    )



    try:
        response = client.chat.completions.create(
            model="nvidia/nemotron-nano-12b-v2-vl:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            extra_body={"reasoning": {"enabled": True}}
            )

        raw = (response.choices[0].message.content or "").strip()

        # Strip markdown fences if model wraps anyway
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()

        plan_data = json.loads(raw)

        update_streak(user_data)
        save_user_data(user_data)

        return jsonify({
            "status":         "success",
            "plan":           plan_data,
            "streak":         user_data["streak"],
            "longest_streak": user_data["longest_streak"],
        })

    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "AI returned malformed JSON — please try again.", "raw": raw}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/save_plan', methods=['POST'])
@login_required
def save_plan():
    body = request.get_json()
    data = load_user_data()
    data['meal_plan'] = body.get('plan_text', '')
    save_user_data(data)
    return jsonify({'status': 'success'})


@app.route('/get_streak')
@login_required
def get_streak():
    data = load_user_data()
    return jsonify({
        'streak':         data.get('streak', 0),
        'longest_streak': data.get('longest_streak', 0),
        'last_plan_date': data.get('last_plan_date'),
    })


# ── Legacy weekly schedule (streaming, kept) ──────────────────────────────────

@app.route('/generate_schedule', methods=['POST'])
@login_required
def generate_schedule():
    import requests as req
    form      = request.get_json()
    user_data = load_user_data()

    goal      = form.get('goal', 'general fitness')
    days      = form.get('days', '3')
    duration  = form.get('duration', '45')
    level     = form.get('level', 'intermediate')
    equipment = form.get('equipment', 'none')
    injuries  = form.get('injuries', 'none')
    allergies = user_data.get('allergies', [])
    weight = form.get('weight', '')
    height = form.get('height', '')
    age = form.get('age', '')
    allergy_note = f"Avoid exercises that aggravate: {', '.join(allergies)}." if allergies else ""

    prompt = (
        f"You are an expert personal trainer. Create a detailed weekly exercise schedule.\n"
        f"Goal: {goal}, Days/week: {days}, Duration: {duration} min, Level: {level}, "
        f"Equipment: {equipment}, Injuries: {injuries}. {allergy_note}\n"
        f"Weight: {weight}, Height: {height}, Age: {age}\n"
        "Format: intro paragraph, each day as a header with warm-up/main/cool-down, rest day rec, recovery tip."
        "Assume you are the role of an expert / professional coach and registered sports dietitian. "
        "Help the user plan what to do, how long to do it for, and how to do it. "
        "The 'plan' array is the full-day meal plan (breakfast through dinner + snacks), "
        "including a clearly labelled pre-workout and post-workout meal. "
        "Respect all allergies. Be specific with quantities and macros. "
        "Write how the user should perform each exercise with coaching cues. Do not include anything outside the schedule." 
        "Tell the user how to perform each stretch or drill in the warm-up and cool-down with coaching cues. " 
        "Keep all responses concise, 1-2 sentences per exercise or stretch. Do not write more than 4 exercises per day. " 
        
    )

    def stream():
        try:
            resp = req.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {OPENROUTER_KEY}',
                    'Content-Type':  'application/json',
                    'HTTP-Referer':  'http://localhost:5000',
                },
                json={
                    'model':    'google/gemma-3-4b-it:free',
                    'stream':   True,
                    'messages': [{'role': 'user', 'content': prompt }]
                },
                stream=True, timeout=90
            )
            for line in resp.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        chunk = line[6:]
                        if chunk == '[DONE]':
                            yield 'data: [DONE]\n\n'; break
                        try:
                            d       = json.loads(chunk)
                            content = d['choices'][0].get('delta', {}).get('content', '')
                            if content:
                                yield f'data: {json.dumps({"content": content})}\n\n'
                        except Exception:
                            pass
        except Exception as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'

    return Response(stream_with_context(stream()), mimetype='text/event-stream')


@app.route('/save_schedule', methods=['POST'])
@login_required
def save_schedule():
    body = request.get_json()
    data = load_user_data()
    data['schedule'] = body.get('schedule', '')
    save_user_data(data)
    return jsonify({'status': 'success'})


# ── Existing data routes ───────────────────────────────────────────────────────

@app.route('/add_meal', methods=['POST'])
@login_required
def add_meal():
    data = load_user_data()
    meal = request.form
    data['diet'].append({
        'name':     meal.get('name', '').strip(),
        'protein':  float(meal.get('protein') or 0),
        'carbs':    float(meal.get('carbs')   or 0),
        'quantity': meal.get('quantity', '').strip()
    })
    save_user_data(data)
    return jsonify({'status': 'success'})

@app.route('/update_hydration', methods=['POST'])
@login_required
def update_hydration():
    data = load_user_data()
    data['hydration']['current'] = max(0, data['hydration']['current'] + int(request.form.get('amount') or 0))
    save_user_data(data)
    return jsonify({'status': 'success'})

@app.route('/add_workout', methods=['POST'])
@login_required
def add_workout():
    data     = load_user_data()
    workout  = request.form
    duration = int(workout.get('duration') or 0)
    data['workouts'].append({
        'type':      workout.get('type', 'Cardio'),
        'duration':  duration,
        'intensity': workout.get('intensity', 'Medium')
    })
    data['points'] += duration * 10
    save_user_data(data)
    return jsonify({'status': 'success', 'points': data['points']})

@app.route('/add_game', methods=['POST'])
@login_required
def add_game():
    data = load_user_data()
    pts  = int(request.form.get('points') or 0)
    data['games'].append({
        'sport':  request.form.get('sport', '').strip(),
        'stats':  request.form.get('stats', '').strip(),
        'points': pts
    })
    data['points'] += pts
    save_user_data(data)
    return jsonify({'status': 'success', 'points': data['points']})

@app.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    data = load_user_data()
    data['allergies'] = [a.strip() for a in request.form.get('allergies', '').split(',') if a.strip()]
    data['goals']     = request.form.get('goals', '').strip()
    save_user_data(data)
    return jsonify({'status': 'success'})

@app.route('/reset_hydration', methods=['POST'])
@login_required
def reset_hydration():
    data = load_user_data()
    data['hydration']['current'] = 0
    save_user_data(data)
    return jsonify({'status': 'success'})


if __name__ == '__main__':
    app.run(debug=True)
