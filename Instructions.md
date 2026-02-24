# Pokémon Home Challenge Tracker - Application Requirements

## Overview
Build a full-stack web application for tracking Pokémon collection progress across generations 1-9, with star challenge tracking, gender variants, shiny status, and user notes. The application must be responsive and work seamlessly on desktop, tablet, and mobile devices.

## Technical Stack
- **Backend**: Python (Flask or FastAPI)
- **Frontend**: HTML/CSS/JavaScript (React or Vue.js recommended for responsiveness)
- **Database**: SQLite or PostgreSQL
- **Authentication**: Secure password hashing (bcrypt or argon2)
- **Deployment**: Browser-accessible web application

## Core Features

### 1. Pokémon Display System
- Display all Pokémon from Generations 1-9 (approximately 1,000+ Pokémon)
- Retrieve sprites from: `https://github.com/PokeAPI/sprites`
  - Use the PokeAPI sprite structure: `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{id}.png`
  - Also support shiny variants: `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/shiny/{id}.png`
- Grid/list view that adapts to screen size
- Search and filter functionality by:
  - Generation
  - Name
  - Type (optional enhancement)
  - Star availability
  - Completion status

### 2. Checkbox System for Each Pokémon

#### Original Generation Checkbox
- Track if the Pokémon has been obtained from its original generation game

#### Gender Checkboxes
- **Male** and **Female** checkboxes only for Pokémon with **visual gender differences**
- Reference: https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_with_gender_differences
- Examples with visual differences: Venusaur (female has smaller seed), Pikachu (female has heart-shaped tail), Hippowdon (different colors)
- Pokémon that can be male/female but have NO visual difference (e.g., Bulbasaur, Ivysaur): do NOT show male/female checkboxes
- Genderless Pokémon (e.g., Beldum, Magnemite, Hoopa): show "Genderless" badge
- **Gender differences count as forms** - Male and Female checkboxes contribute to Form Dex Completion percentage

#### Shiny Checkbox
- Single checkbox to track shiny variant obtained

#### Form Checkboxes
- Display checkboxes for each collectible form a Pokémon has
- Form data source: https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_with_form_differences
- Gender difference data: https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_with_gender_differences
- Only Pokémon with gender differences should show Male/Female checkboxes
- Forms affect the "Form Dex Completion" progress tracker

**Ignored Forms (do not track):**
- Cosplay Pikachu
- Pikachu in a cap (all variants)
- Spiky-eared Pichu
- Kyogre/Groudon Primal forms
- Cherrim Sunshine form
- Arceus type forms
- Darmanitan Zen Mode
- Kyurem Black/White forms
- Meloetta Pirouette forme
- Genesect Drive forms
- Ash-Greninja
- Vivillon Poké Ball Pattern
- Aegislash Blade forme
- Xerneas Active mode
- Zygarde Complete Forme
- Wishiwashi School Form
- Silvally type forms
- Mimikyu Busted Form
- Cramorant Gulping/Gorging forms
- Eiscue Noice Face
- Morpeko Hangry Mode
- Zacian/Zamazenta Crowned forms
- Eternamax Eternatus
- Calyrex Rider forms
- Palafin Hero Form
- Ogerpon mask forms
- Terapagos Terastal/Stellar forms
- All forms under "Form-Like Transformations"
- All forms under "Technical Forms"
- Anything under "Unidentified Properties"

#### Related Stars Checkboxes
- Parse the provided Google Doc to extract star challenges
- Create checkboxes for each applicable star for that Pokémon
- Display star number and tier (Bronze ★, Silver ★, Gold ★, Platinum ★)
- **Star color must match the tier**: Bronze stars display in bronze color, Silver in silver, Gold in gold, Platinum in platinum
- Example format: "☐ Alolan Raichu ★2 (Bronze)"

### 3. Star Challenge Parsing
You need to:
1. Parse the provided document to extract:
   - Pokémon name
   - Star number
   - Star tier (Bronze/Silver/Gold/Platinum)
   - Requirements/description
   - Generation/game requirement

**Important: Star numbers are unique per tier, not globally unique.**
- Bronze Star #1 is different from Silver Star #1, Gold Star #1, and Platinum Star #1
- When storing/looking up star location data, always use (tier, star_number) as the key
- Example: Ho-Oh has Gold #17 (Colosseum Purify All) and Silver #41 (Dream Radar) - these are completely different from Bronze #17 or Bronze #41

2. Create a mapping structure like:
```python
{
    "Pikachu": [
        {
            "star_number": 1,
            "tier": "Bronze",
            "requirement": "Yellow Starter",
            "evolution": "Must not be evolved"
        },
        {
            "star_number": 2,
            "tier": "Bronze",
            "requirement": "Alolan Raichu",
            "evolution": "Must evolve in Alola"
        }
    ]
}
```

3. Handle special cases:
   - Pokémon with multiple stars (like Eevee with 5 different evolutions)
   - Evolution chains (e.g., Zubat/Golbat → Crobat ★6)
   - Regional forms (Alolan, Galarian, Hisuian)
   - Form variations (Vivillon patterns, Furfrou trims, Rotom forms)

### 4. Notes System
- Text area/field for each Pokémon
- Allow users to add custom notes about:
  - Capture location
  - Date obtained
  - Trading history
  - Future plans
- Rich text support (optional)
- Auto-save functionality

### 5. User Authentication & Data Persistence

#### Registration/Login System
- Username and password fields
- Secure password hashing (use bcrypt or argon2)
- Session management
- "Remember me" option

#### Data Storage
- Store per-user:
  - Pokémon collection status (all checkboxes)
  - Notes for each Pokémon
  - Timestamps for tracking
- Database schema:
```sql
users (
    id, 
    username UNIQUE, 
    password_hash, 
    created_at
)

pokemon_tracking (
    id,
    user_id FK,
    pokemon_id,
    original_gen BOOLEAN,
    male BOOLEAN,
    female BOOLEAN,
    shiny BOOLEAN,
    notes TEXT,
    updated_at
)

star_tracking (
    id,
    user_id FK,
    pokemon_id,
    star_number,
    star_tier,
    completed BOOLEAN
)
```

### 6. Responsive Design Requirements

#### Desktop (>1024px)
- Multi-column grid (4-6 Pokémon per row)
- Sidebar for filters
- Expanded view with all details visible

#### Tablet (768px - 1024px)
- 2-3 Pokémon per row
- Collapsible filter menu
- Touch-optimized checkboxes

#### Mobile (<768px)
- Single column list/card view
- Sticky search bar
- Bottom navigation
- Swipe gestures for navigation (optional)
- Expandable Pokémon cards to show details

### 7. Additional Features

#### Progress Tracking
Display four progress boxes:
1. **Master Dex Completion** - Percentage based only on "Original Gen" checkbox being checked
2. **Stars** - Count of completed star challenges
3. **Ghost Stars** - Count based only on "Shiny" checkbox being checked
4. **Form Dex Completion** - Percentage based on form checkboxes being checked (for Pokémon with forms)

Additional features:
- Generation-specific progress bars
- Visual indicators (badges, colors) for completed sections

#### Export/Import
- Export data as JSON or CSV
- Import from backup file

#### Sorting Options
- By National Dex number
- By generation
- By completion status
- By star count
- Alphabetically

## Data Sources

### Pokémon Data
Use PokeAPI (https://pokeapi.co/) to fetch:
- Pokémon names, IDs, types
- Gender ratios
- Sprites (normal and shiny)
- Evolution chains
- Generation information

### Star Challenge Data
Parse from the provided Google Doc:
- Extract all star challenges
- Map to specific Pokémon
- Include tier information
- Store requirements/descriptions

## Technical Implementation Notes

### Frontend
- Use responsive CSS frameworks (Bootstrap, Tailwind, or custom grid)
- Implement lazy loading for images
- Progressive Web App (PWA) capabilities for offline access
- Local storage for draft changes before sync

### Backend
- RESTful API endpoints:
  - `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`
  - `/api/pokemon` (GET all Pokémon with user data)
  - `/api/pokemon/{id}` (GET/PUT specific Pokémon tracking data)
  - `/api/stars` (GET all star challenges)
  - `/api/progress` (GET user statistics)

### Security
- HTTPS only
- CSRF protection
- Rate limiting on API endpoints
- SQL injection prevention (use parameterized queries)
- Password requirements (min length, complexity)

### Performance
- Database indexing on user_id and pokemon_id
- Caching for static Pokémon data
- Pagination for large lists
- Optimized image loading

## Deliverables
1. Fully functional web application
2. User authentication system
3. Complete Pokémon tracking with all checkbox systems
4. Star challenge integration
5. Notes functionality
6. Responsive design for all devices
7. Data persistence and backup capabilities

## Testing Requirements
- Test on multiple browsers (Chrome, Firefox, Safari, Edge)
- Test on multiple devices (desktop, tablet, mobile)
- Test all CRUD operations
- Test authentication flow
- Verify data persistence across sessions

## Location Data Implementation

### Overview
Each Pokemon detail panel shows:
1. **Obtainable Games** - List of valid games for that generation (filtered for version exclusives)
2. **Locations** - Where to catch/obtain the Pokemon in each game

### Data Sources

#### PokeAPI (Primary)
- Provides encounter data for older games (RBY, GSC, RSE base games, DPPt base games)
- Does NOT have data for: LGPE, ORAS, BDSP, BW/B2W2, XY, SM/USUM, SwSh, SV
- Endpoint: `https://pokeapi.co/api/v2/pokemon/{id}/encounters`

#### Manual Location Data (Supplementary)
Since PokeAPI lacks data for many games, manual location objects are defined in `tracker.html`:

| Object | Games Covered | Notes |
|--------|---------------|-------|
| `LGPE_LOCATIONS` | Let's Go Pikachu/Eevee | Gen 1 Pokemon only |
| `ORAS_LOCATIONS` | Ruby/Sapphire/Emerald/Omega Ruby/Alpha Sapphire | Gen 3 Pokemon |
| `BDSP_LOCATIONS` | Diamond/Pearl/Platinum/Brilliant Diamond/Shining Pearl | Gen 4 Pokemon |
| `BW_LOCATIONS` | Black/White/Black 2/White 2 | Gen 5 Pokemon |
| `XY_LOCATIONS` | X/Y | Gen 6 Pokemon |
| `SM_LOCATIONS` | Sun/Moon/Ultra Sun/Ultra Moon | Gen 7 Pokemon |
| `SWSH_LOCATIONS` | Sword/Shield | Gen 8 Pokemon |
| `SV_LOCATIONS` | Scarlet/Violet | Gen 9 Pokemon |

### Version Exclusives Handling
Version exclusive Pokemon use object syntax instead of string:
```javascript
// Available in both versions (string)
25: 'Viridian Forest', // Pikachu

// Version exclusive (object with game keys)
23: { "Let's Go Eevee": 'Route 4, Route 11' }, // Ekans - LGE exclusive
716: { 'X': 'Team Flare HQ' }, // Xerneas - X exclusive
717: { 'Y': 'Team Flare HQ' }, // Yveltal - Y exclusive
```

The `filterValidGames()` function excludes version-exclusive games from the Obtainable Games list.

### Gen 5 Phenomenon Encounters
BW/B2W2 have special encounter methods that should be noted:
- **Rustling Grass** - Random grass shaking (e.g., Audino, Emolga, Stoutland)
- **Dust Clouds** - In caves (e.g., Excadrill, Onix)
- **Rippling Water** - While surfing (e.g., Basculin, Alomomola)
- **Flying Shadows** - On bridges (e.g., Braviary, Mandibuzz, Unfezant)

Reference: https://bulbapedia.bulbagarden.net/wiki/Phenomenon

### Location Name Formatting
- Remove " Area" suffix (e.g., "Route 1 Area" → "Route 1")
- Remove region prefix for single-region generations (e.g., "Kanto Route 1" → "Route 1")
- Exception: Gen 2 keeps both Kanto and Johto prefixes since it spans two regions
- Games are sorted chronologically using `GAME_ORDER` array

### Special Location Types
- **Starter Pokemon** - Gift at game start
- **Gift** - Received from NPC (e.g., "Gift (Gladion, post-game)")
- **Event only** - Special distribution events
- **Evolve** - Evolution only, not catchable wild
- **Trade from X** - Must be transferred from another game
- **Fossil restoration** - Revived from fossils

### Valid Games by Generation
```javascript
GENERATION_GAMES = {
    1: ['Red', 'Blue', 'Yellow', 'FireRed', 'LeafGreen', "Let's Go Pikachu", "Let's Go Eevee"],
    2: ['Gold', 'Silver', 'Crystal', 'HeartGold', 'SoulSilver'],
    3: ['Ruby', 'Sapphire', 'Emerald', 'Omega Ruby', 'Alpha Sapphire'],
    4: ['Diamond', 'Pearl', 'Platinum', 'Brilliant Diamond', 'Shining Pearl'],
    5: ['Black', 'White', 'Black 2', 'White 2'],
    6: ['X', 'Y'],
    7: ['Sun', 'Moon', 'Ultra Sun', 'Ultra Moon'],
    8: ['Sword', 'Shield'],
    9: ['Scarlet', 'Violet'],
}
```

Note: Legends Arceus is added dynamically for Pokemon with Hisuian forms.