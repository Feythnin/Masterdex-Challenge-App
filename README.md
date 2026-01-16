# Pokemon Home Challenge Tracker

A full-stack web application for tracking Pokemon collection progress across all 9 generations, featuring star challenges, form tracking, shiny hunting, and detailed location data.

## Features

### Collection Tracking
- **1025 Pokemon** from Generations 1-9 (complete National Pokedex)
- **Obtained checkbox** - Track Pokemon caught from their original generation games
- **Shiny tracking** - Track shiny variants for base forms and each alternate form
- **Form tracking** - Regional variants (Alolan, Galarian, Hisuian, Paldean), Vivillon patterns, Alcremie creams, and more
- **Gender differences** - Male/Female checkboxes for Pokemon with visual gender differences

### Star Challenges
- Bronze, Silver, Gold, and Platinum tier challenges
- Special achievements like Yellow gifts, Safari Zone catches, Colosseum/XD legendaries
- Color-coded badges matching each tier

### Location Data
- Shows where to catch each Pokemon in valid challenge games
- Version exclusives properly filtered (e.g., Yveltal only shows Y, not X)
- Covers all games: RBY, GSC, RSE, FRLG, DPPt, HGSS, BW/B2W2, XY, ORAS, SM/USUM, LGPE, SwSh, BDSP, SV
- Special encounter methods noted (rustling grass, dust clouds, events)

### Progress Tracking
- **Master Dex Completion** - Percentage of Pokemon obtained
- **Form Dex Completion** - Percentage of forms collected
- **Stars** - Count of completed star challenges
- **Ghost Stars** - Total shiny count (base + forms)

### Additional Features
- Per-Pokemon notes with auto-save
- Search by name or dex number
- Filter by generation or completion status
- Responsive design (desktop, tablet, mobile)
- User accounts with secure authentication

## Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML/CSS/JavaScript (vanilla)
- **Authentication**: Flask-Login with bcrypt password hashing
- **Sprites**: PokeAPI sprite repository

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone or download the repository**
   ```bash
   cd "E:\Master Dex App"
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the app**
   Open your browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

## Usage

### Getting Started
1. Click **Register** to create an account (password must be 8+ characters)
2. Log in with your credentials
3. You'll see the Pokemon tracker grid

### Tracking Pokemon
1. Click any Pokemon card to open the detail panel
2. Check **Obtained** when you've caught it from a valid game
3. Check **Shiny** if you have the shiny variant
4. For Pokemon with forms, check each form you've collected
5. Complete star challenges by checking the star boxes
6. Add notes for personal tracking (auto-saves)

### Filtering & Search
- Use the **search bar** to find Pokemon by name or dex number
- Use the **generation dropdown** to filter by gen
- Use the **status filter** to show completed/incomplete

### Understanding the Display
- Greyed-out sprites = not yet obtained
- Colored sprites = obtained
- Card indicators show: checkmark (obtained), sparkle with count (shinies), form count

## Project Structure

```
E:\Master Dex App\
├── app.py                 # Flask backend (routes, API, models)
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── Instructions.md        # Detailed requirements
├── CURRENT_STATUS.md      # Development progress
├── star_challenges.txt    # Star challenge data
├── instance/
│   └── pokemon_tracker.db # SQLite database (auto-created)
├── templates/
│   ├── base.html          # Base template
│   ├── index.html         # Landing page
│   ├── login.html         # Login form
│   ├── register.html      # Registration form
│   └── tracker.html       # Main tracker (includes location data)
└── static/
    └── style.css          # Responsive styles
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Create new account |
| POST | `/login` | User login |
| GET | `/logout` | User logout |
| GET | `/tracker` | Main tracker page |
| GET | `/api/pokemon` | Get all Pokemon with tracking data |
| PUT | `/api/pokemon/<id>` | Update tracking status |
| PUT | `/api/stars/<pokemon_id>/<star_number>` | Update star completion |
| PUT | `/api/forms/<pokemon_id>/<form_name>` | Update form completion |
| GET | `/api/progress` | Get progress statistics |

## Valid Games by Generation

| Gen | Region | Valid Games |
|-----|--------|-------------|
| 1 | Kanto | Red, Blue, Yellow, FireRed, LeafGreen, Let's Go Pikachu/Eevee |
| 2 | Johto | Gold, Silver, Crystal, HeartGold, SoulSilver |
| 3 | Hoenn | Ruby, Sapphire, Emerald, Omega Ruby, Alpha Sapphire |
| 4 | Sinnoh | Diamond, Pearl, Platinum, Brilliant Diamond, Shining Pearl |
| 5 | Unova | Black, White, Black 2, White 2 |
| 6 | Kalos | X, Y |
| 7 | Alola | Sun, Moon, Ultra Sun, Ultra Moon |
| 8 | Galar | Sword, Shield |
| 9 | Paldea | Scarlet, Violet |

## Data Sources

- **Pokemon Data**: Hardcoded in `app.py` with sprites from PokeAPI
- **Location Data**: Combination of PokeAPI encounters + manual data in `tracker.html`
- **Star Challenges**: Parsed from community challenge document into `star_challenges.txt`

## Security

- Passwords hashed with bcrypt (never stored in plain text)
- Session-based authentication with Flask-Login
- SQL injection prevention via SQLAlchemy ORM

## Browser Support

Tested on:
- Chrome
- Firefox
- Safari
- Edge

## License

This project is for personal use for tracking Pokemon collection progress.

Pokemon and all related properties are trademarks of Nintendo/Game Freak/The Pokemon Company.
