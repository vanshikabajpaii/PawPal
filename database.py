"""
database.py — PawPal SQLite database module.

Handles schema creation, sample data seeding, and full CRUD
operations for pets, adopters, adoption applications, and
vaccinations.  Every public function is safe to call from any
thread because a new connection is obtained (and closed) per call.
"""

import sqlite3
import os
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# Database path
# ---------------------------------------------------------------------------
_DB_DIR  = os.path.join(os.path.dirname(__file__), "database")
_DB_PATH = os.path.join(_DB_DIR, "pawpal.db")


# ---------------------------------------------------------------------------
# Custom Row & Connection helper
# ---------------------------------------------------------------------------

class DbRow(sqlite3.Row):
    """Enhanced sqlite3.Row supporting dict-like .get(), key aliases, and contains."""

    _ALIASES = {
        "id": ("pet_id", "adopter_id", "application_id", "vaccination_id"),
        "date_given": ("vaccination_date",),
        "adoption_date": ("application_date",),
    }

    def __getitem__(self, key):
        if isinstance(key, str):
            try:
                return super().__getitem__(key)
            except (KeyError, IndexError):
                if key in self._ALIASES:
                    for alias in self._ALIASES[key]:
                        try:
                            return super().__getitem__(alias)
                        except (KeyError, IndexError):
                            pass
                raise KeyError(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        try:
            val = self[key]
            if val is None and default is not None:
                return default
            return val
        except (KeyError, IndexError):
            return default

    def __contains__(self, key):
        if key in self.keys():
            return True
        if key in self._ALIASES:
            return any(alias in self.keys() for alias in self._ALIASES[key])
        return False


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with foreign-key support enabled."""
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = DbRow
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS pets (
    pet_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    species         TEXT    NOT NULL,
    breed           TEXT,
    age             REAL,
    gender          TEXT,
    description     TEXT,
    color           TEXT,
    status          TEXT    DEFAULT 'Available',
    image_path      TEXT,
    date_registered TEXT    DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS adopters (
    adopter_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name       TEXT    NOT NULL,
    phone           TEXT,
    email           TEXT    UNIQUE,
    address         TEXT,
    date_registered TEXT    DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS adoption_applications (
    application_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id          INTEGER NOT NULL,
    adopter_id      INTEGER NOT NULL,
    application_date TEXT   DEFAULT (date('now')),
    status          TEXT    DEFAULT 'Pending',
    notes           TEXT,
    FOREIGN KEY (pet_id)      REFERENCES pets(pet_id)      ON DELETE CASCADE,
    FOREIGN KEY (adopter_id)  REFERENCES adopters(adopter_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vaccinations (
    vaccination_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id          INTEGER NOT NULL,
    vaccine_name    TEXT    NOT NULL,
    vaccination_date TEXT,
    next_due_date    TEXT,
    notes           TEXT,
    FOREIGN KEY (pet_id) REFERENCES pets(pet_id) ON DELETE CASCADE
);
"""


def initialize_database() -> None:
    """Create all tables (if they do not already exist) and migrate schema."""
    try:
        conn = get_connection()
        conn.executescript(_DDL)
        conn.commit()
        # Schema migration: ensure 'color' column exists in existing pets table
        try:
            conn.execute("ALTER TABLE pets ADD COLUMN color TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        conn.close()
    except sqlite3.Error as exc:
        print(f"[database] initialize_database error: {exc}")
        raise


# ---------------------------------------------------------------------------
# Sample data seeding
# ---------------------------------------------------------------------------

def seed_sample_data() -> None:
    """Populate the database with sample records (runs only once)."""
    try:
        conn = get_connection()

        # Guard: only seed if pets table is empty
        if conn.execute("SELECT COUNT(*) FROM pets").fetchone()[0] > 0:
            conn.close()
            return

        today   = date.today().isoformat()
        past_30 = (date.today() - timedelta(days=30)).isoformat()
        past_60 = (date.today() - timedelta(days=60)).isoformat()
        past_90 = (date.today() - timedelta(days=90)).isoformat()

        # ---- Pets (8) -------------------------------------------------------
        pets = [
            # name, species, breed, age, gender, description, status, image_path
            ("Buddy",    "Dog",    "Golden Retriever", 2.5, "Male",
             "Friendly and loves to play fetch. Great with kids.",
             "Available", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "buddy.png")),

            ("Luna",     "Cat",    "Siamese",          1.0, "Female",
             "Calm and affectionate. Enjoys curling up on laps.",
             "Available", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "luna.png")),

            ("Max",      "Dog",    "German Shepherd",  4.0, "Male",
             "Well-trained and loyal. Needs an active household.",
             "Adopted", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "max.png")),

            ("Daisy",    "Cat",    "Persian",          3.0, "Female",
             "Quiet and gentle. Loves being brushed.",
             "Adopted", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "daisy.png")),

            ("Charlie",  "Dog",    "Beagle",           1.5, "Male",
             "Curious and energetic. Loves outdoor adventures.",
             "Available", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "charlie.png")),

            ("Bella",    "Rabbit", "Holland Lop",      0.5, "Female",
             "Tiny and playful. Perfectly litter-trained.",
             "Available", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "bella.png")),

            ("Oliver",   "Cat",    "Maine Coon",       2.0, "Male",
             "Big and fluffy. Very sociable with people.",
             "Available", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "oliver.png")),

            ("Coco",     "Rabbit", "Lionhead",         1.0, "Female",
             "Adorable fluffy mane. Loves veggies and cuddles.",
             "Available", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "coco.png")),
        ]

        pet_dates = [today, today, past_60, past_90, past_30, today, past_30, today]
        pet_ids   = []
        for idx, (name, species, breed, age, gender, desc, status, img) in enumerate(pets):
            cur = conn.execute(
                """INSERT INTO pets
                   (name, species, breed, age, gender, description, status, image_path, date_registered)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, species, breed, age, gender, desc, status, img, pet_dates[idx])
            )
            pet_ids.append(cur.lastrowid)

        # ---- Adopters (3) ---------------------------------------------------
        adopters = [
            ("Alice Johnson", "555-0101", "alice@example.com",  "12 Oak Street, Springfield"),
            ("Bob Martinez",  "555-0202", "bob@example.com",    "45 Maple Ave, Shelbyville"),
            ("Carol Lee",     "555-0303", "carol@example.com",  "78 Pine Road, Capital City"),
        ]
        adopter_ids = []
        for full_name, phone, email, address in adopters:
            cur = conn.execute(
                """INSERT INTO adopters (full_name, phone, email, address)
                   VALUES (?, ?, ?, ?)""",
                (full_name, phone, email, address)
            )
            adopter_ids.append(cur.lastrowid)

        # ---- Adoption applications (2 approved) ----------------------------
        # Max (index 2, status=Adopted) → Alice;  Daisy (index 3) → Bob
        approved_apps = [
            (pet_ids[2], adopter_ids[0], past_60, "Approved",
             "Max found his forever home with Alice."),
            (pet_ids[3], adopter_ids[1], past_90, "Approved",
             "Daisy is now living happily with Bob."),
        ]
        for pet_id, adopter_id, app_date, status, notes in approved_apps:
            conn.execute(
                """INSERT INTO adoption_applications
                   (pet_id, adopter_id, application_date, status, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (pet_id, adopter_id, app_date, status, notes)
            )

        # ---- Vaccinations (5) ----------------------------------------------
        future_30 = (date.today() + timedelta(days=30)).isoformat()
        future_60 = (date.today() + timedelta(days=60)).isoformat()
        vaccinations = [
            (pet_ids[0], "Rabies",      past_30, future_30, "Annual booster"),
            (pet_ids[0], "DHPP",        past_60, future_60, "Combo vaccine"),
            (pet_ids[1], "FVRCP",       past_30, future_30, "Cat combo vaccine"),
            (pet_ids[4], "Rabies",      past_30, future_30, "Annual booster"),
            (pet_ids[6], "Feline Leuk", past_60, future_60, "FeLV vaccine"),
        ]
        for pet_id, vaccine_name, vdate, next_due, notes in vaccinations:
            conn.execute(
                """INSERT INTO vaccinations
                   (pet_id, vaccine_name, vaccination_date, next_due_date, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (pet_id, vaccine_name, vdate, next_due, notes)
            )

        conn.commit()
        conn.close()
        print("[database] Sample data seeded successfully.")

    except sqlite3.Error as exc:
        print(f"[database] seed_sample_data error: {exc}")
        raise


# ===========================================================================
# PETS CRUD
# ===========================================================================

def add_pet(name: str, species: str, breed: str = None, age: float = None,
            gender: str = None, description: str = None,
            status: str = "Available", image_path: str = None,
            color: str = None, date_registered: str = None, **kwargs) -> int:
    """Insert a new pet. Returns the new pet_id."""
    try:
        conn = get_connection()
        if date_registered:
            cur  = conn.execute(
                """INSERT INTO pets (name, species, breed, age, gender, description, color, status, image_path, date_registered)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, species, breed, age, gender, description, color, status, image_path, date_registered)
            )
        else:
            cur  = conn.execute(
                """INSERT INTO pets (name, species, breed, age, gender, description, color, status, image_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, species, breed, age, gender, description, color, status, image_path)
            )
        conn.commit()
        pet_id = cur.lastrowid
        conn.close()
        return pet_id
    except sqlite3.Error as exc:
        print(f"[database] add_pet error: {exc}")
        raise


def get_all_pets() -> list:
    """Return all pets as a list of Row objects."""
    try:
        conn = get_connection()
        rows = conn.execute("SELECT * FROM pets ORDER BY date_registered DESC").fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] get_all_pets error: {exc}")
        return []


def get_pet_by_id(pet_id: int):
    """Return a single pet Row or None."""
    try:
        conn = get_connection()
        row  = conn.execute("SELECT * FROM pets WHERE pet_id = ?", (pet_id,)).fetchone()
        conn.close()
        return row
    except sqlite3.Error as exc:
        print(f"[database] get_pet_by_id error: {exc}")
        return None


def update_pet(pet_id: int, name: str, species: str, breed: str = None,
               age: float = None, gender: str = None, description: str = None,
               status: str = "Available", image_path: str = None,
               color: str = None, **kwargs) -> bool:
    """Update an existing pet. Returns True on success."""
    try:
        conn = get_connection()
        conn.execute(
            """UPDATE pets SET name=?, species=?, breed=?, age=?, gender=?,
               description=?, color=?, status=?, image_path=?
               WHERE pet_id=?""",
            (name, species, breed, age, gender, description, color, status, image_path, pet_id)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as exc:
        print(f"[database] update_pet error: {exc}")
        return False


def delete_pet(pet_id: int) -> bool:
    """Delete a pet (cascades to applications and vaccinations)."""
    try:
        conn = get_connection()
        conn.execute("DELETE FROM pets WHERE pet_id = ?", (pet_id,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as exc:
        print(f"[database] delete_pet error: {exc}")
        return False


def search_pets(query: str) -> list:
    """Full-text search across name, species, breed, description, and color."""
    try:
        conn  = get_connection()
        like  = f"%{query}%"
        rows  = conn.execute(
            """SELECT * FROM pets
               WHERE name LIKE ? OR species LIKE ? OR breed LIKE ? OR description LIKE ? OR color LIKE ?
               ORDER BY name""",
            (like, like, like, like, like)
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] search_pets error: {exc}")
        return []


def get_pets_by_status(status: str) -> list:
    """Return pets filtered by status ('Available', 'Adopted', 'Pending')."""
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM pets WHERE status = ? ORDER BY name", (status,)
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] get_pets_by_status error: {exc}")
        return []


# ===========================================================================
# ADOPTERS CRUD
# ===========================================================================

def add_adopter(full_name: str, phone: str = None, email: str = None,
                address: str = None, date_registered: str = None, **kwargs) -> int:
    """Insert a new adopter. Returns the new adopter_id."""
    try:
        conn = get_connection()
        if date_registered:
            cur  = conn.execute(
                "INSERT INTO adopters (full_name, phone, email, address, date_registered) VALUES (?, ?, ?, ?, ?)",
                (full_name, phone, email, address, date_registered)
            )
        else:
            cur  = conn.execute(
                "INSERT INTO adopters (full_name, phone, email, address) VALUES (?, ?, ?, ?)",
                (full_name, phone, email, address)
            )
        conn.commit()
        adopter_id = cur.lastrowid
        conn.close()
        return adopter_id
    except sqlite3.Error as exc:
        print(f"[database] add_adopter error: {exc}")
        raise


def get_all_adopters() -> list:
    """Return all adopters ordered by registration date."""
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM adopters ORDER BY date_registered DESC"
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] get_all_adopters error: {exc}")
        return []


def get_adopter_by_id(adopter_id: int):
    """Return a single adopter Row or None."""
    try:
        conn = get_connection()
        row  = conn.execute(
            "SELECT * FROM adopters WHERE adopter_id = ?", (adopter_id,)
        ).fetchone()
        conn.close()
        return row
    except sqlite3.Error as exc:
        print(f"[database] get_adopter_by_id error: {exc}")
        return None


def update_adopter(adopter_id: int, full_name: str, phone: str = None,
                   email: str = None, address: str = None, **kwargs) -> bool:
    """Update an existing adopter. Returns True on success."""
    try:
        conn = get_connection()
        conn.execute(
            "UPDATE adopters SET full_name=?, phone=?, email=?, address=? WHERE adopter_id=?",
            (full_name, phone, email, address, adopter_id)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as exc:
        print(f"[database] update_adopter error: {exc}")
        return False


def delete_adopter(adopter_id: int) -> bool:
    """Delete an adopter (cascades to their applications)."""
    try:
        conn = get_connection()
        conn.execute("DELETE FROM adopters WHERE adopter_id = ?", (adopter_id,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as exc:
        print(f"[database] delete_adopter error: {exc}")
        return False


def search_adopters(query: str) -> list:
    """Search adopters by name, email, phone, or address."""
    try:
        conn = get_connection()
        like = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM adopters
               WHERE full_name LIKE ? OR email LIKE ? OR phone LIKE ? OR address LIKE ?
               ORDER BY full_name""",
            (like, like, like, like)
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] search_adopters error: {exc}")
        return []


# ===========================================================================
# ADOPTION APPLICATIONS CRUD
# ===========================================================================

def add_application(pet_id: int, adopter_id: int, notes: str = None,
                    application_date: str = None, status: str = "Pending", **kwargs) -> int:
    """Create a new adoption application. Returns the new application_id."""
    try:
        conn = get_connection()
        if application_date:
            cur  = conn.execute(
                """INSERT INTO adoption_applications (pet_id, adopter_id, application_date, status, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (pet_id, adopter_id, application_date, status, notes)
            )
        else:
            cur  = conn.execute(
                """INSERT INTO adoption_applications (pet_id, adopter_id, notes)
                   VALUES (?, ?, ?)""",
                (pet_id, adopter_id, notes)
            )
        conn.commit()
        app_id = cur.lastrowid
        conn.close()
        return app_id
    except sqlite3.Error as exc:
        print(f"[database] add_application error: {exc}")
        raise


def get_all_applications() -> list:
    """Return all applications joined with pet and adopter names."""
    try:
        conn = get_connection()
        rows = conn.execute(
            """SELECT aa.*, p.name AS pet_name, a.full_name AS adopter_name
               FROM adoption_applications aa
               JOIN pets     p ON aa.pet_id     = p.pet_id
               JOIN adopters a ON aa.adopter_id = a.adopter_id
               ORDER BY aa.application_date DESC"""
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] get_all_applications error: {exc}")
        return []


def get_applications_by_pet(pet_id: int) -> list:
    """Return all applications for a specific pet."""
    try:
        conn = get_connection()
        rows = conn.execute(
            """SELECT aa.*, a.full_name AS adopter_name
               FROM adoption_applications aa
               JOIN adopters a ON aa.adopter_id = a.adopter_id
               WHERE aa.pet_id = ?
               ORDER BY aa.application_date DESC""",
            (pet_id,)
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] get_applications_by_pet error: {exc}")
        return []


def get_applications_by_adopter(adopter_id: int) -> list:
    """Return all applications submitted by a specific adopter."""
    try:
        conn = get_connection()
        rows = conn.execute(
            """SELECT aa.*, p.name AS pet_name
               FROM adoption_applications aa
               JOIN pets p ON aa.pet_id = p.pet_id
               WHERE aa.adopter_id = ?
               ORDER BY aa.application_date DESC""",
            (adopter_id,)
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] get_applications_by_adopter error: {exc}")
        return []


def update_application_status(application_id: int, status: str,
                               notes: str = None) -> bool:
    """Update the status (and optionally notes) of an application."""
    try:
        conn = get_connection()
        if notes is not None:
            conn.execute(
                "UPDATE adoption_applications SET status=?, notes=? WHERE application_id=?",
                (status, notes, application_id)
            )
        else:
            conn.execute(
                "UPDATE adoption_applications SET status=? WHERE application_id=?",
                (status, application_id)
            )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as exc:
        print(f"[database] update_application_status error: {exc}")
        return False


def approve_application(application_id: int) -> bool:
    """Approve an application and mark the pet as 'Adopted'."""
    try:
        conn = get_connection()
        # Fetch the pet_id for this application
        row = conn.execute(
            "SELECT pet_id FROM adoption_applications WHERE application_id = ?",
            (application_id,)
        ).fetchone()
        if not row:
            conn.close()
            return False
        pet_id = row["pet_id"]

        # Approve the application
        conn.execute(
            "UPDATE adoption_applications SET status='Approved' WHERE application_id=?",
            (application_id,)
        )
        # Mark pet as Adopted
        conn.execute(
            "UPDATE pets SET status='Adopted' WHERE pet_id=?",
            (pet_id,)
        )
        # Reject any other pending applications for the same pet
        conn.execute(
            """UPDATE adoption_applications SET status='Rejected'
               WHERE pet_id=? AND application_id != ? AND status='Pending'""",
            (pet_id, application_id)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as exc:
        print(f"[database] approve_application error: {exc}")
        return False


def reject_application(application_id: int, notes: str = None) -> bool:
    """Reject an adoption application."""
    try:
        conn = get_connection()
        conn.execute(
            "UPDATE adoption_applications SET status='Rejected', notes=? WHERE application_id=?",
            (notes, application_id)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as exc:
        print(f"[database] reject_application error: {exc}")
        return False


def get_adoption_history() -> list:
    """Return all approved adoptions with pet and adopter details."""
    try:
        conn = get_connection()
        rows = conn.execute(
            """SELECT aa.*, p.name AS pet_name, p.species, p.breed,
                      a.full_name AS adopter_name, a.email AS adopter_email
               FROM adoption_applications aa
               JOIN pets     p ON aa.pet_id     = p.pet_id
               JOIN adopters a ON aa.adopter_id = a.adopter_id
               WHERE aa.status = 'Approved'
               ORDER BY aa.application_date DESC"""
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] get_adoption_history error: {exc}")
        return []


# ===========================================================================
# VACCINATIONS CRUD
# ===========================================================================

def add_vaccination(pet_id: int, vaccine_name: str,
                    vaccination_date: str = None,
                    next_due_date: str = None,
                    notes: str = None,
                    date_given: str = None, **kwargs) -> int:
    """Insert a new vaccination record. Returns the new vaccination_id."""
    vdate = vaccination_date if vaccination_date is not None else date_given
    try:
        conn = get_connection()
        cur  = conn.execute(
            """INSERT INTO vaccinations
               (pet_id, vaccine_name, vaccination_date, next_due_date, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (pet_id, vaccine_name, vdate, next_due_date, notes)
        )
        conn.commit()
        vac_id = cur.lastrowid
        conn.close()
        return vac_id
    except sqlite3.Error as exc:
        print(f"[database] add_vaccination error: {exc}")
        raise


def get_all_vaccinations() -> list:
    """Return all vaccination records joined with pet name."""
    try:
        conn = get_connection()
        rows = conn.execute(
            """SELECT v.*, p.name AS pet_name, p.species
               FROM vaccinations v
               JOIN pets p ON v.pet_id = p.pet_id
               ORDER BY v.next_due_date"""
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] get_all_vaccinations error: {exc}")
        return []


def get_vaccinations_by_pet(pet_id: int) -> list:
    """Return all vaccination records for a specific pet."""
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM vaccinations WHERE pet_id = ? ORDER BY vaccination_date DESC",
            (pet_id,)
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] get_vaccinations_by_pet error: {exc}")
        return []


def update_vaccination(vaccination_id: int = None, vaccine_name: str = None,
                       vaccination_date: str = None,
                       next_due_date: str = None,
                       notes: str = None,
                       vacc_id: int = None,
                       date_given: str = None,
                       pet_id: int = None, **kwargs) -> bool:
    """Update an existing vaccination record."""
    vid = vaccination_id if vaccination_id is not None else vacc_id
    vdate = vaccination_date if vaccination_date is not None else date_given
    try:
        conn = get_connection()
        if pet_id is not None:
            conn.execute(
                """UPDATE vaccinations
                   SET pet_id=?, vaccine_name=?, vaccination_date=?, next_due_date=?, notes=?
                   WHERE vaccination_id=?""",
                (pet_id, vaccine_name, vdate, next_due_date, notes, vid)
            )
        else:
            conn.execute(
                """UPDATE vaccinations
                   SET vaccine_name=?, vaccination_date=?, next_due_date=?, notes=?
                   WHERE vaccination_id=?""",
                (vaccine_name, vdate, next_due_date, notes, vid)
            )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as exc:
        print(f"[database] update_vaccination error: {exc}")
        return False


def delete_vaccination(vaccination_id: int) -> bool:
    """Delete a vaccination record."""
    try:
        conn = get_connection()
        conn.execute(
            "DELETE FROM vaccinations WHERE vaccination_id = ?", (vaccination_id,)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as exc:
        print(f"[database] delete_vaccination error: {exc}")
        return False


def get_upcoming_vaccinations(days: int = 30) -> list:
    """Return vaccinations due within the next *days* days."""
    try:
        conn   = get_connection()
        today  = date.today().isoformat()
        cutoff = (date.today() + timedelta(days=days)).isoformat()
        rows   = conn.execute(
            """SELECT v.*, p.name AS pet_name, p.species
               FROM vaccinations v
               JOIN pets p ON v.pet_id = p.pet_id
               WHERE v.next_due_date BETWEEN ? AND ?
               ORDER BY v.next_due_date""",
            (today, cutoff)
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as exc:
        print(f"[database] get_upcoming_vaccinations error: {exc}")
        return []


# ===========================================================================
# DASHBOARD STATS
# ===========================================================================

def get_dashboard_stats() -> dict:
    """
    Return aggregate statistics for the dashboard.

    Keys
    ----
    total_pets            int
    available_pets        int
    adopted_pets          int
    pending_applications  int
    recent_pets           list[Row]  — last 5 registered
    species_distribution  dict       — {species: count}
    monthly_adoptions     list[dict] — last 6 months [{month, count}]
    """
    try:
        conn = get_connection()

        total_pets = conn.execute(
            "SELECT COUNT(*) FROM pets"
        ).fetchone()[0]

        available_pets = conn.execute(
            "SELECT COUNT(*) FROM pets WHERE status = 'Available'"
        ).fetchone()[0]

        adopted_pets = conn.execute(
            "SELECT COUNT(*) FROM pets WHERE status = 'Adopted'"
        ).fetchone()[0]

        pending_applications = conn.execute(
            "SELECT COUNT(*) FROM adoption_applications WHERE status = 'Pending'"
        ).fetchone()[0]

        recent_pets = conn.execute(
            "SELECT * FROM pets ORDER BY date_registered DESC LIMIT 5"
        ).fetchall()

        # Species distribution
        species_rows = conn.execute(
            "SELECT species, COUNT(*) AS cnt FROM pets GROUP BY species"
        ).fetchall()
        species_distribution = {row["species"]: row["cnt"] for row in species_rows}

        # Monthly adoptions — last 6 calendar months
        monthly_adoptions = []
        for i in range(5, -1, -1):
            # Calculate the first day of the month i months ago
            ref   = date.today().replace(day=1)
            month = ref.month - i
            year  = ref.year
            while month <= 0:
                month += 12
                year  -= 1
            month_str   = f"{year}-{month:02d}"
            count = conn.execute(
                """SELECT COUNT(*) FROM adoption_applications
                   WHERE status = 'Approved'
                   AND strftime('%Y-%m', application_date) = ?""",
                (month_str,)
            ).fetchone()[0]
            # Human-readable label e.g. "Nov 2026"
            label = datetime(year, month, 1).strftime("%b %Y")
            monthly_adoptions.append({"month": label, "count": count})

        conn.close()
        return {
            "total_pets":           total_pets,
            "available_pets":       available_pets,
            "adopted_pets":         adopted_pets,
            "pending_applications": pending_applications,
            "recent_pets":          recent_pets,
            "species_distribution": species_distribution,
            "monthly_adoptions":    monthly_adoptions,
        }

    except sqlite3.Error as exc:
        print(f"[database] get_dashboard_stats error: {exc}")
        return {
            "total_pets":           0,
            "available_pets":       0,
            "adopted_pets":         0,
            "pending_applications": 0,
            "recent_pets":          [],
            "species_distribution": {},
            "monthly_adoptions":    [],
        }


# ---------------------------------------------------------------------------
# Convenience Aliases and Helpers for Modules
# ---------------------------------------------------------------------------

get_pet = get_pet_by_id
get_adopter = get_adopter_by_id


def get_available_pets() -> list:
    """Return all pets with status 'Available'."""
    return get_pets_by_status("Available")


def get_application(application_id: int):
    """Return a single application by ID joined with pet and adopter names."""
    try:
        conn = get_connection()
        row = conn.execute(
            """SELECT aa.*, p.name AS pet_name, a.full_name AS adopter_name
               FROM adoption_applications aa
               JOIN pets p ON aa.pet_id = p.pet_id
               JOIN adopters a ON aa.adopter_id = a.adopter_id
               WHERE aa.application_id = ?""",
            (application_id,)
        ).fetchone()
        conn.close()
        return row
    except sqlite3.Error as exc:
        print(f"[database] get_application error: {exc}")
        return None


def get_vaccination(vaccination_id: int):
    """Return a single vaccination record by ID joined with pet name."""
    try:
        conn = get_connection()
        row = conn.execute(
            """SELECT v.*, p.name AS pet_name, p.species
               FROM vaccinations v
               JOIN pets p ON v.pet_id = p.pet_id
               WHERE v.vaccination_id = ?""",
            (vaccination_id,)
        ).fetchone()
        conn.close()
        return row
    except sqlite3.Error as exc:
        print(f"[database] get_vaccination error: {exc}")
        return None


def get_pet_adoption_status(pet_name: str) -> str:
    """Return the status string for a pet by name."""
    try:
        conn = get_connection()
        row = conn.execute(
            "SELECT status FROM pets WHERE LOWER(name) = LOWER(?)",
            (pet_name,)
        ).fetchone()
        conn.close()
        return row["status"] if row else "Unknown"
    except sqlite3.Error:
        return "Unknown"


def get_recent_pets(limit: int = 5) -> list:
    """Return the last `limit` registered pets."""
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM pets ORDER BY date_registered DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return rows
    except sqlite3.Error:
        return []


def get_species_distribution() -> list:
    """Return species distribution as a list of (species, count) tuples."""
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT species, COUNT(*) AS cnt FROM pets GROUP BY species ORDER BY cnt DESC"
        ).fetchall()
        conn.close()
        return [(r["species"], r["cnt"]) for r in rows]
    except sqlite3.Error:
        return []


def get_monthly_adoptions(months: int = 6) -> list:
    """Return monthly approved adoptions as a list of (label, count) tuples."""
    try:
        conn = get_connection()
        monthly = []
        for i in range(months - 1, -1, -1):
            ref = date.today().replace(day=1)
            month = ref.month - i
            year = ref.year
            while month <= 0:
                month += 12
                year -= 1
            month_str = f"{year}-{month:02d}"
            count = conn.execute(
                """SELECT COUNT(*) FROM adoption_applications
                   WHERE status = 'Approved'
                   AND strftime('%Y-%m', application_date) = ?""",
                (month_str,)
            ).fetchone()[0]
            label = datetime(year, month, 1).strftime("%b %Y")
            monthly.append((label, count))
        conn.close()
        return monthly
    except sqlite3.Error:
        return []


# ---------------------------------------------------------------------------
# Module entry point — initialise and seed on import when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    initialize_database()
    seed_sample_data()
    stats = get_dashboard_stats()
    print("Dashboard stats:", stats)
