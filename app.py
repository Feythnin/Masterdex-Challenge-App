from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
import bcrypt
from datetime import datetime
import os
import csv
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pokemon_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Import Pokemon data from separate module
from pokemon_data import GENERATION_GAMES, POKEMON_DATA, POKEMON_BY_ID

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('tracker'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
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

# API Endpoints
@app.route('/api/pokemon', methods=['GET'])
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
        pokemon_data['star_tracking'] = {
            s.star_number: s.completed for s in star_tracking
        }
        pokemon_data['form_tracking'] = {
            f.form_name: f.completed for f in form_tracking
        }
        pokemon_data['form_shiny_tracking'] = {
            f.form_name: f.shiny for f in form_tracking
        }
        result.append(pokemon_data)

    return jsonify(result)

@app.route('/api/pokemon/<int:pokemon_id>', methods=['PUT'])
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

    return jsonify({'message': 'Star updated successfully'})

@app.route('/api/forms/<int:pokemon_id>/<form_name>', methods=['PUT'])
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
@login_required
def get_progress():
    total_pokemon = len(POKEMON_DATA)

    # Get all user tracking data in one query for efficiency
    all_tracking = {t.pokemon_id: t for t in PokemonTracking.query.filter_by(user_id=current_user.id).all()}

    # Master Dex Completion - only counts original_gen checkbox
    master_dex_completed = sum(1 for t in all_tracking.values() if t.original_gen)

    # Stars completed
    stars_completed = StarTracking.query.filter_by(
        user_id=current_user.id,
        completed=True
    ).count()

    # Ghost Stars - counts shiny Pokemon (base form + all form shinies)
    ghost_stars = sum(1 for t in all_tracking.values() if t.shiny)
    ghost_stars += FormTracking.query.filter_by(
        user_id=current_user.id,
        shiny=True
    ).count()

    # Form Dex Completion - count total forms and completed forms
    # Include gender differences as forms (male + female = 2 forms per Pokemon with gender diff)
    total_forms = sum(len(p['forms']) for p in POKEMON_DATA)
    total_forms += sum(2 for p in POKEMON_DATA if p.get('has_gender_diff'))

    # All forms (including Male/Female gender forms) are now tracked in FormTracking
    forms_completed = FormTracking.query.filter_by(
        user_id=current_user.id,
        completed=True
    ).count()

    # Generation-specific progress
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

    return jsonify({
        'total_pokemon': total_pokemon,
        'master_dex_completed': master_dex_completed,
        'master_dex_percentage': (master_dex_completed / total_pokemon * 100) if total_pokemon > 0 else 0,
        'stars_completed': stars_completed,
        'ghost_stars': ghost_stars,
        'total_forms': total_forms,
        'forms_completed': forms_completed,
        'form_dex_percentage': (forms_completed / total_forms * 100) if total_forms > 0 else 0,
        'gen_progress': gen_progress
    })

@app.route('/api/bulk', methods=['POST'])
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Run migration for existing male/female data
        migrate_gender_to_forms()
    app.run(debug=True, port=5000)
