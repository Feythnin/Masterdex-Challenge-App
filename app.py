from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import bcrypt
from datetime import datetime
import os
import csv
import io

app = Flask(__name__)

# Security: SECRET_KEY must be set in production
# In development, a random key is generated (sessions won't persist across restarts)
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    import secrets
    secret_key = secrets.token_hex(32)
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError("SECRET_KEY environment variable must be set in production!")
app.config['SECRET_KEY'] = secret_key

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pokemon_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Security: Session cookie settings
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Prevent CSRF via cross-site requests

db = SQLAlchemy(app)

# Security: CORS - restrict to same origin in production, allow all in development
cors_origins = os.environ.get('CORS_ORIGINS', '*' if os.environ.get('FLASK_ENV') != 'production' else None)
if cors_origins:
    CORS(app, origins=cors_origins.split(','), supports_credentials=True)

# Security: CSRF protection
csrf = CSRFProtect(app)

# Security: Rate limiting
# Note: default_limits apply to ALL routes. Keep them generous for authenticated API usage
# (checkbox toggles, progress refreshes). Login/register have their own strict limits.
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["5000 per hour"],
    storage_uri="memory://"
)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    pokemon_tracking = db.relationship('PokemonTracking', backref='user', lazy=True)
    star_tracking = db.relationship('StarTracking', backref='user', lazy=True)
    form_tracking = db.relationship('FormTracking', backref='user', lazy=True)

class PokemonTracking(db.Model):
    __tablename__ = 'pokemon_tracking'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pokemon_id = db.Column(db.Integer, nullable=False)
    original_gen = db.Column(db.Boolean, default=False)
    male = db.Column(db.Boolean, default=False)
    female = db.Column(db.Boolean, default=False)
    shiny = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'pokemon_id', name='unique_user_pokemon'),)

class StarTracking(db.Model):
    __tablename__ = 'star_tracking'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pokemon_id = db.Column(db.Integer, nullable=False)
    star_number = db.Column(db.Integer, nullable=False)
    star_tier = db.Column(db.String(20), nullable=False)
    completed = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'pokemon_id', 'star_number', name='unique_user_pokemon_star'),)

class FormTracking(db.Model):
    __tablename__ = 'form_tracking'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pokemon_id = db.Column(db.Integer, nullable=False)
    form_name = db.Column(db.String(50), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    shiny = db.Column(db.Boolean, default=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'pokemon_id', 'form_name', name='unique_user_pokemon_form'),)

class Friendship(db.Model):
    __tablename__ = 'friendships'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),
        db.CheckConstraint('user_id < friend_id', name='friendship_ordering'),
    )

class FriendRequest(db.Model):
    __tablename__ = 'friend_requests'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_requests')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_requests')

class UserPrivacy(db.Model):
    __tablename__ = 'user_privacy'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    profile_visibility = db.Column(db.String(20), default='friends', nullable=False)
    show_stats = db.Column(db.Boolean, default=True)
    show_forms = db.Column(db.Boolean, default=True)
    show_stars = db.Column(db.Boolean, default=True)
    show_shinies = db.Column(db.Boolean, default=True)
    show_notes = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('privacy', uselist=False))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Import Pokemon data from separate module
from pokemon_data import GENERATION_GAMES, POKEMON_DATA, POKEMON_BY_ID, get_chain_members, POKEMON_TO_CHAIN


# Helper functions for friends system
def are_friends(user_id_1, user_id_2):
    low, high = min(user_id_1, user_id_2), max(user_id_1, user_id_2)
    return Friendship.query.filter_by(user_id=low, friend_id=high).first() is not None

def get_privacy(user_id):
    privacy = UserPrivacy.query.filter_by(user_id=user_id).first()
    if not privacy:
        privacy = UserPrivacy(user_id=user_id)
        db.session.add(privacy)
        db.session.commit()
    return privacy

def can_view_profile(viewer_id, target_user):
    privacy = get_privacy(target_user.id)
    if privacy.profile_visibility == 'public':
        return True
    if privacy.profile_visibility == 'friends':
        return are_friends(viewer_id, target_user.id)
    return False  # private

def calculate_user_progress(user_id):
    total_pokemon = len(POKEMON_DATA)
    all_tracking = {t.pokemon_id: t for t in PokemonTracking.query.filter_by(user_id=user_id).all()}
    master_dex_completed = sum(1 for t in all_tracking.values() if t.original_gen)

    all_stars = StarTracking.query.filter_by(user_id=user_id, completed=True).all()
    counted_star_keys = set()
    stars_completed = 0
    for star in all_stars:
        pokemon = POKEMON_BY_ID.get(star.pokemon_id)
        if not pokemon:
            continue
        star_def = next((s for s in pokemon.get('stars', []) if s['star_number'] == star.star_number), None)
        if star_def:
            if star_def.get('chain_shared'):
                chain_name = POKEMON_TO_CHAIN.get(star.pokemon_id, str(star.pokemon_id))
                key = (star.star_number, chain_name)
            else:
                key = (star.star_number, star.pokemon_id)
            if key not in counted_star_keys:
                counted_star_keys.add(key)
                stars_completed += 1

    ghost_stars = sum(1 for t in all_tracking.values() if t.shiny)
    ghost_stars += FormTracking.query.filter_by(user_id=user_id, shiny=True).count()

    total_forms = sum(len(p['forms']) for p in POKEMON_DATA)
    total_forms += sum(2 for p in POKEMON_DATA if p.get('has_gender_diff'))
    forms_completed = FormTracking.query.filter_by(user_id=user_id, completed=True).count()

    gen_progress = {}
    for gen in range(1, 10):
        gen_pokemon = [p for p in POKEMON_DATA if p['generation'] == gen]
        gen_total = len(gen_pokemon)
        gen_completed = sum(1 for p in gen_pokemon if all_tracking.get(p['id']) and all_tracking[p['id']].original_gen)
        gen_progress[gen] = {
            'total': gen_total,
            'completed': gen_completed,
            'percentage': (gen_completed / gen_total * 100) if gen_total > 0 else 0
        }

    return {
        'total_pokemon': total_pokemon,
        'master_dex_completed': master_dex_completed,
        'master_dex_percentage': (master_dex_completed / total_pokemon * 100) if total_pokemon > 0 else 0,
        'stars_completed': stars_completed,
        'ghost_stars': ghost_stars,
        'total_forms': total_forms,
        'forms_completed': forms_completed,
        'form_dex_percentage': (forms_completed / total_forms * 100) if total_forms > 0 else 0,
        'gen_progress': gen_progress
    }


# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('tracker'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
@csrf.exempt  # Using JSON API with SameSite cookies
def register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400

        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400

        # Case-insensitive username check
        if User.query.filter(db.func.lower(User.username) == username.lower()).first():
            return jsonify({'error': 'Username already exists'}), 400

        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = User(username=username, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return jsonify({'message': 'Registration successful', 'redirect': '/tracker'})

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
@csrf.exempt  # Using JSON API with SameSite cookies
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        remember = data.get('remember', False)

        # Case-insensitive username lookup
        user = User.query.filter(db.func.lower(User.username) == username.lower()).first()

        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            login_user(user, remember=remember)
            return jsonify({'message': 'Login successful', 'redirect': '/tracker'})

        return jsonify({'error': 'Invalid username or password'}), 401

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/tracker')
@login_required
def tracker():
    return render_template('tracker.html')

# API Endpoints - exempt from CSRF (JSON API with SameSite cookies provides protection)
@app.route('/api/pokemon', methods=['GET'])
@csrf.exempt
@login_required
def get_pokemon():
    # Fetch all user data in 3 bulk queries instead of 3 per Pokemon
    all_tracking = PokemonTracking.query.filter_by(user_id=current_user.id).all()
    all_stars = StarTracking.query.filter_by(user_id=current_user.id).all()
    all_forms = FormTracking.query.filter_by(user_id=current_user.id).all()

    # Index by pokemon_id for fast lookup
    tracking_by_id = {t.pokemon_id: t for t in all_tracking}
    stars_by_id = {}
    for s in all_stars:
        if s.pokemon_id not in stars_by_id:
            stars_by_id[s.pokemon_id] = []
        stars_by_id[s.pokemon_id].append(s)
    forms_by_id = {}
    for f in all_forms:
        if f.pokemon_id not in forms_by_id:
            forms_by_id[f.pokemon_id] = []
        forms_by_id[f.pokemon_id].append(f)

    result = []
    for pokemon in POKEMON_DATA:
        pokemon_id = pokemon['id']
        tracking = tracking_by_id.get(pokemon_id)
        star_tracking = stars_by_id.get(pokemon_id, [])
        form_tracking = forms_by_id.get(pokemon_id, [])

        pokemon_data = pokemon.copy()
        # Pokemon 899-905 are Legends Arceus exclusive (not in Sword/Shield)
        if 899 <= pokemon['id'] <= 905:
            valid_games = ['Legends Arceus']
        else:
            valid_games = GENERATION_GAMES.get(pokemon['generation'], [])[:]  # Copy the list
            # Add Legends Arceus for Pokemon with Hisuian forms
            if any('Hisuian' in form for form in pokemon.get('forms', [])):
                valid_games.append('Legends Arceus')
        pokemon_data['valid_games'] = valid_games
        pokemon_data['tracking'] = {
            'original_gen': tracking.original_gen if tracking else False,
            'male': tracking.male if tracking else False,
            'female': tracking.female if tracking else False,
            'shiny': tracking.shiny if tracking else False,
            'notes': tracking.notes if tracking else ''
        }

        # Build effective_stars (including inherited chain_shared stars from evolution chain members)
        effective_stars = list(pokemon.get('stars', []))
        chain_members = get_chain_members(pokemon_id)

        # Add inherited chain_shared stars from other chain members
        for member_id in chain_members:
            if member_id == pokemon_id:
                continue
            member = POKEMON_BY_ID.get(member_id)
            if member:
                for star in member.get('stars', []):
                    if star.get('chain_shared'):
                        inherited_star = star.copy()
                        inherited_star['inherited_from'] = member_id
                        inherited_star['inherited_from_name'] = member['name']
                        effective_stars.append(inherited_star)

        pokemon_data['effective_stars'] = effective_stars

        # Build effective_star_tracking (include chain member completions for chain_shared stars)
        effective_star_tracking = {s.star_number: s.completed for s in star_tracking}
        for member_id in chain_members:
            if member_id != pokemon_id:
                member_stars = stars_by_id.get(member_id, [])
                for s in member_stars:
                    member = POKEMON_BY_ID.get(member_id)
                    if member:
                        star_def = next((star for star in member.get('stars', [])
                            if star['star_number'] == s.star_number and star.get('chain_shared')), None)
                        if star_def and s.completed:
                            effective_star_tracking[s.star_number] = True

        pokemon_data['star_tracking'] = effective_star_tracking
        pokemon_data['form_tracking'] = {
            f.form_name: f.completed for f in form_tracking
        }
        pokemon_data['form_shiny_tracking'] = {
            f.form_name: f.shiny for f in form_tracking
        }
        result.append(pokemon_data)

    return jsonify(result)

@app.route('/api/pokemon/<int:pokemon_id>', methods=['PUT'])
@csrf.exempt
@login_required
def update_pokemon(pokemon_id):
    data = request.get_json()

    tracking = PokemonTracking.query.filter_by(
        user_id=current_user.id,
        pokemon_id=pokemon_id
    ).first()

    if not tracking:
        tracking = PokemonTracking(user_id=current_user.id, pokemon_id=pokemon_id)
        db.session.add(tracking)

    if 'original_gen' in data:
        tracking.original_gen = data['original_gen']
    if 'male' in data:
        tracking.male = data['male']
    if 'female' in data:
        tracking.female = data['female']
    if 'shiny' in data:
        tracking.shiny = data['shiny']
    if 'notes' in data:
        tracking.notes = data['notes']

    db.session.commit()

    return jsonify({'message': 'Updated successfully'})

@app.route('/api/stars/<int:pokemon_id>/<int:star_number>', methods=['PUT'])
@csrf.exempt
@login_required
def update_star(pokemon_id, star_number):
    data = request.get_json()

    star = StarTracking.query.filter_by(
        user_id=current_user.id,
        pokemon_id=pokemon_id,
        star_number=star_number
    ).first()

    if not star:
        star = StarTracking(
            user_id=current_user.id,
            pokemon_id=pokemon_id,
            star_number=star_number,
            star_tier=data.get('tier', 'Bronze')
        )
        db.session.add(star)

    star.completed = data.get('completed', False)
    db.session.commit()

    # Determine if this star is chain_shared and return chain info
    pokemon = POKEMON_BY_ID.get(pokemon_id)
    star_def = next((s for s in pokemon.get('stars', []) if s['star_number'] == star_number), None) if pokemon else None
    chain_shared = star_def.get('chain_shared', False) if star_def else False
    chain_members = get_chain_members(pokemon_id) if chain_shared else [pokemon_id]

    return jsonify({
        'message': 'Star updated successfully',
        'chain_members': chain_members,
        'chain_shared': chain_shared
    })

@app.route('/api/forms/<int:pokemon_id>/<form_name>', methods=['PUT'])
@csrf.exempt
@login_required
def update_form(pokemon_id, form_name):
    data = request.get_json()

    form = FormTracking.query.filter_by(
        user_id=current_user.id,
        pokemon_id=pokemon_id,
        form_name=form_name
    ).first()

    if not form:
        form = FormTracking(
            user_id=current_user.id,
            pokemon_id=pokemon_id,
            form_name=form_name
        )
        db.session.add(form)

    # Update completed if provided
    if 'completed' in data:
        form.completed = data.get('completed', False)
    # Update shiny if provided
    if 'shiny' in data:
        form.shiny = data.get('shiny', False)
    db.session.commit()

    return jsonify({'message': 'Form updated successfully'})

@app.route('/api/progress', methods=['GET'])
@csrf.exempt
@login_required
def get_progress():
    return jsonify(calculate_user_progress(current_user.id))

@app.route('/api/bulk', methods=['POST'])
@csrf.exempt
@login_required
def bulk_update():
    data = request.json
    pokemon_ids = data.get('pokemon_ids', [])
    field = data.get('field')  # 'original_gen' or 'shiny'
    value = data.get('value', False)  # True or False

    if not pokemon_ids or field not in ['original_gen', 'shiny']:
        return jsonify({'error': 'Invalid request'}), 400

    updated_count = 0

    for pokemon_id in pokemon_ids:
        tracking = PokemonTracking.query.filter_by(
            user_id=current_user.id,
            pokemon_id=pokemon_id
        ).first()

        if not tracking:
            tracking = PokemonTracking(user_id=current_user.id, pokemon_id=pokemon_id)
            db.session.add(tracking)

        if field == 'original_gen':
            tracking.original_gen = value
        elif field == 'shiny':
            tracking.shiny = value

        updated_count += 1

    db.session.commit()
    return jsonify({'success': True, 'updated': updated_count})

@app.route('/api/export', methods=['GET'])
@csrf.exempt
@login_required
def export_data():
    # Get all user tracking data
    all_tracking = {t.pokemon_id: t for t in PokemonTracking.query.filter_by(user_id=current_user.id).all()}
    all_stars = {}
    for s in StarTracking.query.filter_by(user_id=current_user.id).all():
        if s.pokemon_id not in all_stars:
            all_stars[s.pokemon_id] = []
        all_stars[s.pokemon_id].append(s)
    all_forms = {}
    for f in FormTracking.query.filter_by(user_id=current_user.id).all():
        if f.pokemon_id not in all_forms:
            all_forms[f.pokemon_id] = []
        all_forms[f.pokemon_id].append(f)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row (gender forms are now included in forms_completed/forms_shiny)
    writer.writerow(['pokemon_id', 'pokemon_name', 'obtained', 'shiny', 'notes', 'forms_completed', 'forms_shiny', 'stars_completed'])

    # Data rows
    for pokemon in POKEMON_DATA:
        pid = pokemon['id']
        tracking = all_tracking.get(pid)
        stars = all_stars.get(pid, [])
        forms = all_forms.get(pid, [])

        # Get completed forms and shiny forms as pipe-separated lists
        # This now includes Male/Female gender forms stored in FormTracking
        forms_completed = '|'.join([f.form_name for f in forms if f.completed])
        forms_shiny = '|'.join([f.form_name for f in forms if f.shiny])
        stars_completed = '|'.join([str(s.star_number) for s in stars if s.completed])

        writer.writerow([
            pid,
            pokemon['name'],
            'true' if tracking and tracking.original_gen else 'false',
            'true' if tracking and tracking.shiny else 'false',
            tracking.notes if tracking and tracking.notes else '',
            forms_completed,
            forms_shiny,
            stars_completed
        ])

    # Return as CSV file download
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=pokemon_tracker_export_{current_user.username}.csv'}
    )

@app.route('/api/import', methods=['POST'])
@csrf.exempt
@login_required
def import_data():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400

    try:
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)

        imported_count = 0

        for row in reader:
            pokemon_id = int(row['pokemon_id'])

            # Update or create PokemonTracking
            tracking = PokemonTracking.query.filter_by(
                user_id=current_user.id,
                pokemon_id=pokemon_id
            ).first()

            if not tracking:
                tracking = PokemonTracking(user_id=current_user.id, pokemon_id=pokemon_id)
                db.session.add(tracking)

            tracking.original_gen = row.get('obtained', '').lower() == 'true'
            tracking.shiny = row.get('shiny', '').lower() == 'true'
            tracking.notes = row.get('notes', '')

            # Backward compatibility: handle old CSV format with male/female columns
            # Convert them to FormTracking entries
            pokemon_data = next((p for p in POKEMON_DATA if p['id'] == pokemon_id), None)
            if pokemon_data and pokemon_data.get('has_gender_diff'):
                if row.get('male', '').lower() == 'true':
                    form = FormTracking.query.filter_by(
                        user_id=current_user.id,
                        pokemon_id=pokemon_id,
                        form_name='Male'
                    ).first()
                    if not form:
                        form = FormTracking(user_id=current_user.id, pokemon_id=pokemon_id, form_name='Male')
                        db.session.add(form)
                    form.completed = True

                if row.get('female', '').lower() == 'true':
                    form = FormTracking.query.filter_by(
                        user_id=current_user.id,
                        pokemon_id=pokemon_id,
                        form_name='Female'
                    ).first()
                    if not form:
                        form = FormTracking(user_id=current_user.id, pokemon_id=pokemon_id, form_name='Female')
                        db.session.add(form)
                    form.completed = True

            # Handle forms completed (includes Male/Female in new format)
            forms_completed = row.get('forms_completed', '')
            if forms_completed:
                for form_name in forms_completed.split('|'):
                    if form_name:
                        form = FormTracking.query.filter_by(
                            user_id=current_user.id,
                            pokemon_id=pokemon_id,
                            form_name=form_name
                        ).first()
                        if not form:
                            form = FormTracking(user_id=current_user.id, pokemon_id=pokemon_id, form_name=form_name)
                            db.session.add(form)
                        form.completed = True

            # Handle forms shiny
            forms_shiny = row.get('forms_shiny', '')
            if forms_shiny:
                for form_name in forms_shiny.split('|'):
                    if form_name:
                        form = FormTracking.query.filter_by(
                            user_id=current_user.id,
                            pokemon_id=pokemon_id,
                            form_name=form_name
                        ).first()
                        if not form:
                            form = FormTracking(user_id=current_user.id, pokemon_id=pokemon_id, form_name=form_name)
                            db.session.add(form)
                        form.shiny = True

            # Handle stars completed
            stars_completed = row.get('stars_completed', '')
            if stars_completed:
                # Get Pokemon data to find star tiers
                pokemon_data = next((p for p in POKEMON_DATA if p['id'] == pokemon_id), None)
                if pokemon_data:
                    for star_num_str in stars_completed.split('|'):
                        if star_num_str:
                            star_num = int(star_num_str)
                            # Find the tier for this star
                            star_info = next((s for s in pokemon_data.get('stars', []) if s['star_number'] == star_num), None)
                            if star_info:
                                star = StarTracking.query.filter_by(
                                    user_id=current_user.id,
                                    pokemon_id=pokemon_id,
                                    star_number=star_num
                                ).first()
                                if not star:
                                    star = StarTracking(
                                        user_id=current_user.id,
                                        pokemon_id=pokemon_id,
                                        star_number=star_num,
                                        star_tier=star_info['tier']
                                    )
                                    db.session.add(star)
                                star.completed = True

            imported_count += 1

        db.session.commit()
        return jsonify({'success': True, 'imported': imported_count})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Friends page routes
@app.route('/friends')
@login_required
def friends_page():
    return render_template('friends.html')

@app.route('/friends/<username>')
@login_required
def friend_profile(username):
    return render_template('profile.html', profile_username=username)

# Friends API endpoints
@app.route('/api/users/search', methods=['GET'])
@csrf.exempt
@login_required
@limiter.limit("30 per minute")
def search_users():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    users = User.query.filter(
        User.username.ilike(f'%{q}%'),
        User.id != current_user.id
    ).limit(20).all()
    results = []
    for u in users:
        # Check existing relationship
        friendship_status = None
        if are_friends(current_user.id, u.id):
            friendship_status = 'friends'
        else:
            req = FriendRequest.query.filter(
                db.or_(
                    db.and_(FriendRequest.sender_id == current_user.id, FriendRequest.receiver_id == u.id),
                    db.and_(FriendRequest.sender_id == u.id, FriendRequest.receiver_id == current_user.id)
                ),
                FriendRequest.status == 'pending'
            ).first()
            if req:
                friendship_status = 'pending_sent' if req.sender_id == current_user.id else 'pending_received'
        results.append({
            'id': u.id,
            'username': u.username,
            'friendship_status': friendship_status
        })
    return jsonify(results)

@app.route('/api/friends', methods=['GET'])
@csrf.exempt
@login_required
def get_friends():
    # Get all friendships
    friendships = Friendship.query.filter(
        db.or_(Friendship.user_id == current_user.id, Friendship.friend_id == current_user.id)
    ).all()
    friends = []
    for f in friendships:
        friend_id = f.friend_id if f.user_id == current_user.id else f.user_id
        friend_user = User.query.get(friend_id)
        if friend_user:
            friends.append({
                'id': friend_user.id,
                'username': friend_user.username,
                'since': f.created_at.isoformat()
            })

    # Get incoming requests
    incoming = FriendRequest.query.filter_by(receiver_id=current_user.id, status='pending').all()
    incoming_list = [{
        'id': r.id,
        'sender_id': r.sender_id,
        'username': r.sender.username,
        'created_at': r.created_at.isoformat()
    } for r in incoming]

    # Get outgoing requests
    outgoing = FriendRequest.query.filter_by(sender_id=current_user.id, status='pending').all()
    outgoing_list = [{
        'id': r.id,
        'receiver_id': r.receiver_id,
        'username': r.receiver.username,
        'created_at': r.created_at.isoformat()
    } for r in outgoing]

    return jsonify({
        'friends': friends,
        'incoming': incoming_list,
        'outgoing': outgoing_list
    })

@app.route('/api/friends/request-count', methods=['GET'])
@csrf.exempt
@login_required
def friend_request_count():
    count = FriendRequest.query.filter_by(receiver_id=current_user.id, status='pending').count()
    return jsonify({'count': count})

@app.route('/api/friends/request', methods=['POST'])
@csrf.exempt
@login_required
@limiter.limit("20 per minute")
def send_friend_request():
    data = request.get_json()
    username = data.get('username', '').strip()
    target = User.query.filter(db.func.lower(User.username) == username.lower()).first()
    if not target:
        return jsonify({'error': 'User not found'}), 404
    if target.id == current_user.id:
        return jsonify({'error': 'Cannot send friend request to yourself'}), 400
    if are_friends(current_user.id, target.id):
        return jsonify({'error': 'Already friends'}), 400

    # Check for existing pending request from current user
    existing = FriendRequest.query.filter_by(
        sender_id=current_user.id, receiver_id=target.id, status='pending'
    ).first()
    if existing:
        return jsonify({'error': 'Request already sent'}), 400

    # Check for reverse pending request — auto-accept
    reverse = FriendRequest.query.filter_by(
        sender_id=target.id, receiver_id=current_user.id, status='pending'
    ).first()
    if reverse:
        reverse.status = 'accepted'
        reverse.updated_at = datetime.utcnow()
        low, high = min(current_user.id, target.id), max(current_user.id, target.id)
        friendship = Friendship(user_id=low, friend_id=high)
        db.session.add(friendship)
        db.session.commit()
        return jsonify({'message': 'Friend request auto-accepted', 'auto_accepted': True})

    req = FriendRequest(sender_id=current_user.id, receiver_id=target.id)
    db.session.add(req)
    db.session.commit()
    return jsonify({'message': 'Friend request sent'})

@app.route('/api/friends/request/<int:request_id>', methods=['PUT'])
@csrf.exempt
@login_required
def respond_friend_request(request_id):
    freq = FriendRequest.query.get(request_id)
    if not freq or freq.receiver_id != current_user.id:
        return jsonify({'error': 'Request not found'}), 404
    if freq.status != 'pending':
        return jsonify({'error': 'Request already handled'}), 400

    data = request.get_json()
    action = data.get('action')
    if action not in ('accept', 'decline'):
        return jsonify({'error': 'Invalid action'}), 400

    freq.status = 'accepted' if action == 'accept' else 'declined'
    freq.updated_at = datetime.utcnow()

    if action == 'accept':
        low, high = min(current_user.id, freq.sender_id), max(current_user.id, freq.sender_id)
        friendship = Friendship(user_id=low, friend_id=high)
        db.session.add(friendship)

    db.session.commit()
    return jsonify({'message': f'Request {action}ed'})

@app.route('/api/friends/request/<int:request_id>', methods=['DELETE'])
@csrf.exempt
@login_required
def cancel_friend_request(request_id):
    freq = FriendRequest.query.get(request_id)
    if not freq or freq.sender_id != current_user.id:
        return jsonify({'error': 'Request not found'}), 404
    if freq.status != 'pending':
        return jsonify({'error': 'Request already handled'}), 400
    db.session.delete(freq)
    db.session.commit()
    return jsonify({'message': 'Request cancelled'})

@app.route('/api/friends/<int:user_id>', methods=['DELETE'])
@csrf.exempt
@login_required
def remove_friend(user_id):
    low, high = min(current_user.id, user_id), max(current_user.id, user_id)
    friendship = Friendship.query.filter_by(user_id=low, friend_id=high).first()
    if not friendship:
        return jsonify({'error': 'Not friends'}), 404
    db.session.delete(friendship)
    db.session.commit()
    return jsonify({'message': 'Friend removed'})

@app.route('/api/friends/<username>/profile', methods=['GET'])
@csrf.exempt
@login_required
def get_friend_profile(username):
    target = User.query.filter(db.func.lower(User.username) == username.lower()).first()
    if not target:
        return jsonify({'error': 'User not found'}), 404

    if target.id == current_user.id:
        return jsonify({'error': 'Use /api/progress for your own profile'}), 400

    if not can_view_profile(current_user.id, target):
        privacy = get_privacy(target.id)
        return jsonify({'error': 'Profile is private', 'visibility': privacy.profile_visibility}), 403

    privacy = get_privacy(target.id)
    progress = calculate_user_progress(target.id)

    # Build profile data respecting privacy settings
    profile = {
        'username': target.username,
        'privacy': {
            'show_stats': privacy.show_stats,
            'show_forms': privacy.show_forms,
            'show_stars': privacy.show_stars,
            'show_shinies': privacy.show_shinies,
            'show_notes': privacy.show_notes,
        }
    }

    if privacy.show_stats:
        profile['stats'] = progress

    # Build pokemon list
    all_tracking = {t.pokemon_id: t for t in PokemonTracking.query.filter_by(user_id=target.id).all()}
    all_stars = {}
    for s in StarTracking.query.filter_by(user_id=target.id).all():
        if s.pokemon_id not in all_stars:
            all_stars[s.pokemon_id] = []
        all_stars[s.pokemon_id].append(s)
    all_forms = {}
    for f in FormTracking.query.filter_by(user_id=target.id).all():
        if f.pokemon_id not in all_forms:
            all_forms[f.pokemon_id] = []
        all_forms[f.pokemon_id].append(f)

    pokemon_list = []
    for pokemon in POKEMON_DATA:
        pid = pokemon['id']
        tracking = all_tracking.get(pid)
        stars = all_stars.get(pid, [])
        forms = all_forms.get(pid, [])

        entry = {
            'id': pid,
            'name': pokemon['name'],
            'generation': pokemon['generation'],
            'types': pokemon.get('types', []),
            'obtained': tracking.original_gen if tracking else False,
        }

        if privacy.show_shinies:
            entry['shiny'] = tracking.shiny if tracking else False
            entry['form_shinies'] = {f.form_name: f.shiny for f in forms if f.shiny}

        if privacy.show_stars:
            # Build effective stars with chain sharing
            effective_stars = list(pokemon.get('stars', []))
            chain_members = get_chain_members(pid)
            for member_id in chain_members:
                if member_id == pid:
                    continue
                member = POKEMON_BY_ID.get(member_id)
                if member:
                    for star in member.get('stars', []):
                        if star.get('chain_shared'):
                            inherited_star = star.copy()
                            inherited_star['inherited_from'] = member_id
                            inherited_star['inherited_from_name'] = member['name']
                            effective_stars.append(inherited_star)

            effective_star_tracking = {s.star_number: s.completed for s in stars}
            for member_id in chain_members:
                if member_id != pid:
                    member_stars = all_stars.get(member_id, [])
                    for s in member_stars:
                        member = POKEMON_BY_ID.get(member_id)
                        if member:
                            star_def = next((star for star in member.get('stars', [])
                                if star['star_number'] == s.star_number and star.get('chain_shared')), None)
                            if star_def and s.completed:
                                effective_star_tracking[s.star_number] = True

            entry['effective_stars'] = effective_stars
            entry['star_tracking'] = effective_star_tracking

        if privacy.show_forms:
            entry['forms'] = pokemon.get('forms', [])
            entry['has_gender_diff'] = pokemon.get('has_gender_diff', False)
            entry['form_tracking'] = {f.form_name: f.completed for f in forms}

        if privacy.show_notes:
            entry['notes'] = tracking.notes if tracking and tracking.notes else ''

        pokemon_list.append(entry)

    profile['pokemon'] = pokemon_list
    return jsonify(profile)

@app.route('/api/privacy', methods=['GET'])
@csrf.exempt
@login_required
def get_privacy_settings():
    privacy = get_privacy(current_user.id)
    return jsonify({
        'profile_visibility': privacy.profile_visibility,
        'show_stats': privacy.show_stats,
        'show_forms': privacy.show_forms,
        'show_stars': privacy.show_stars,
        'show_shinies': privacy.show_shinies,
        'show_notes': privacy.show_notes,
    })

@app.route('/api/privacy', methods=['PUT'])
@csrf.exempt
@login_required
def update_privacy_settings():
    data = request.get_json()
    privacy = get_privacy(current_user.id)

    if 'profile_visibility' in data:
        if data['profile_visibility'] in ('public', 'friends', 'private'):
            privacy.profile_visibility = data['profile_visibility']
    for field in ('show_stats', 'show_forms', 'show_stars', 'show_shinies', 'show_notes'):
        if field in data:
            setattr(privacy, field, bool(data[field]))

    db.session.commit()
    return jsonify({'message': 'Privacy settings updated'})


def migrate_gender_to_forms():
    """Migrate existing male/female tracking data to FormTracking entries."""
    # Get all Pokemon with gender differences
    gender_diff_pokemon_ids = {p['id'] for p in POKEMON_DATA if p.get('has_gender_diff')}

    # Find all PokemonTracking entries with male or female checked
    tracking_entries = PokemonTracking.query.filter(
        db.or_(PokemonTracking.male == True, PokemonTracking.female == True)
    ).all()

    migrated_count = 0
    for tracking in tracking_entries:
        # Only migrate if this Pokemon actually has gender differences
        if tracking.pokemon_id not in gender_diff_pokemon_ids:
            continue

        # Migrate male
        if tracking.male:
            existing = FormTracking.query.filter_by(
                user_id=tracking.user_id,
                pokemon_id=tracking.pokemon_id,
                form_name='Male'
            ).first()
            if not existing:
                form_entry = FormTracking(
                    user_id=tracking.user_id,
                    pokemon_id=tracking.pokemon_id,
                    form_name='Male',
                    completed=True,
                    shiny=False
                )
                db.session.add(form_entry)
                migrated_count += 1

        # Migrate female
        if tracking.female:
            existing = FormTracking.query.filter_by(
                user_id=tracking.user_id,
                pokemon_id=tracking.pokemon_id,
                form_name='Female'
            ).first()
            if not existing:
                form_entry = FormTracking(
                    user_id=tracking.user_id,
                    pokemon_id=tracking.pokemon_id,
                    form_name='Female',
                    completed=True,
                    shiny=False
                )
                db.session.add(form_entry)
                migrated_count += 1

    if migrated_count > 0:
        db.session.commit()
        print(f"Migrated {migrated_count} gender form entries to FormTracking")

    return migrated_count

def init_db():
    """Create tables and run migrations. Called on startup regardless of entry point."""
    with app.app_context():
        db.create_all()
        # Run migration for existing male/female data
        migrate_gender_to_forms()

init_db()

if __name__ == '__main__':
    # Security: Debug mode only enabled if FLASK_DEBUG=1 is set
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, port=5000)
