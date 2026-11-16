# 🐾 PawPal — Pet Adoption & Care Management System

> A desktop application for managing pet adoptions, vaccinations, and care records — built with Python and Tkinter.

---

## 📋 Description

PawPal is a full-featured, offline-first desktop application designed to help pet shelters and adoption centers manage their daily operations. It provides an intuitive graphical interface for tracking pets, handling adoption applications, recording vaccination histories, and generating visual analytics — all powered by a local SQLite database with zero external service dependencies.

---

## ✨ Features

- 🏠 **Dashboard** — At-a-glance statistics and recent activity overview
- 🐶 **Pet Management** — Add, edit, delete, and search pets with full profile details
- 📝 **Adoption Workflow** — Submit, review, approve, or reject adoption applications
- 💉 **Vaccination Tracking** — Maintain vaccination history and get upcoming-due alerts
- 📊 **Reports & Analytics** — Interactive charts (species distribution, adoption trends, vaccination summaries)
- 🗄️ **SQLite Database** — Local, file-based storage — no server or internet connection required
- 🎨 **Pastel UI** — Clean, friendly color palette designed for everyday shelter staff use

---

## 📸 Screenshots

> _Screenshots will be added after the first release._
>
> Planned captures:
> - Dashboard overview
> - Pets management table
> - Add/Edit pet form
> - Adoptions workflow
> - Reports with live charts

---

## 📦 Requirements

| Requirement | Version |
|-------------|---------|
| Python      | 3.11+   |
| customtkinter | ≥ 5.2.0 |
| Pillow      | ≥ 10.0.0 |
| matplotlib  | ≥ 3.7.0  |

> [!NOTE]
> PawPal uses only the **standard `tkinter`** library for its core window and widgets. `customtkinter` and `Pillow` are listed for optional theme enhancements and image support.

---

## 🚀 Installation & Running

### 1. Install Python 3.11+

Download from [python.org](https://www.python.org/downloads/) and ensure Python is added to your system PATH.

### 2. Navigate to the project folder

```bash
cd path/to/PawPal
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Launch the application

```bash
python main.py
```

The application window will open maximized and automatically seed sample data on first run.

---

## 🗂️ Project Structure

```
PawPal/
├── main.py                     # Application entry point
├── database.py                 # SQLite database module (all CRUD)
├── requirements.txt            # Python package dependencies
├── README.md                   # This file
│
├── assets/
│   ├── icons/
│   │   └── paw.ico             # Optional window icon
│   └── images/                 # Pet images (future feature)
│
├── database/
│   └── pawpal.db               # Auto-created SQLite database
│
├── modules/
│   ├── dashboard.py            # Dashboard module
│   ├── pets.py                 # Pets management module
│   ├── adoptions.py            # Adoptions module
│   ├── vaccinations.py         # Vaccinations module
│   └── reports.py              # Reports & Analytics module
│
├── ui/
│   ├── sidebar.py              # Navigation sidebar widget
│   └── theme.py                # Shared color palette & styles
│
└── tests/
    └── test_database.py        # Unit tests for database operations
```

---

## 📂 Module Descriptions

### `main.py`
The root application file. Instantiates the `PawPalApp` Tk window, sets up the sidebar and content frame, initialises all five modules, seeds the database on first run, and handles navigation between modules.

### `database.py`
Central data access layer. Manages all SQLite operations using a per-call connection pattern (thread-safe). Provides:
- `initialize_database()` — creates tables
- `seed_sample_data()` — populates demo records (runs once)
- Full CRUD for **pets**, **adopters**, **adoption applications**, and **vaccinations**
- `get_dashboard_stats()` — aggregated statistics for the dashboard

### `modules/dashboard.py`
Displays summary statistics cards and a recent activity feed. Refreshed automatically on every navigation visit.

### `modules/pets.py`
Full pets management with a searchable/filterable table, an add/edit form with validation, and a delete action with confirmation.

### `modules/adoptions.py`
Adoption workflow manager. Lists all applications with status badges, allows submitting new applications, and provides Approve / Reject controls with business-rule enforcement (a pet can only be adopted once).

### `modules/vaccinations.py`
Vaccination record tracker. Shows upcoming-due vaccines highlighted in the table, with add/edit/delete functionality tied to individual pets.

### `modules/reports.py`
Analytics page featuring four Matplotlib charts embedded in the Tk window:
1. Species distribution (pie)
2. Adoption status breakdown (donut)
3. Monthly adoptions over the last 6 months (bar)
4. Top vaccine types by frequency (horizontal bar)

Plus a summary statistics panel at the bottom.

### `ui/sidebar.py`
Fixed-width navigation sidebar with labeled buttons for each module. Highlights the active section and triggers the `navigate()` callback on the main app.

### `ui/theme.py`
Shared color constants and optional font/style helpers used across all modules.

---

## 🗃️ Database Schema

```sql
pets (
    pet_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    species         TEXT    NOT NULL,
    breed           TEXT,
    age             REAL,
    gender          TEXT,
    description     TEXT,
    status          TEXT    DEFAULT 'Available',
    image_path      TEXT,
    date_registered TEXT    DEFAULT (date('now'))
);

adopters (
    adopter_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name       TEXT    NOT NULL,
    phone           TEXT,
    email           TEXT    UNIQUE,
    address         TEXT,
    date_registered TEXT    DEFAULT (date('now'))
);

adoption_applications (
    application_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id          INTEGER NOT NULL  REFERENCES pets(pet_id)      ON DELETE CASCADE,
    adopter_id      INTEGER NOT NULL  REFERENCES adopters(adopter_id) ON DELETE CASCADE,
    application_date TEXT   DEFAULT (date('now')),
    status          TEXT   DEFAULT 'Pending',
    notes           TEXT
);

vaccinations (
    vaccination_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id          INTEGER NOT NULL  REFERENCES pets(pet_id) ON DELETE CASCADE,
    vaccine_name    TEXT    NOT NULL,
    vaccination_date TEXT,
    next_due_date    TEXT,
    notes           TEXT
);
```

---

## 📖 Usage Guide

### Dashboard
- Opens automatically on launch.
- Shows total pets, available pets, adopted count, and pending applications.
- Displays the 5 most recently registered pets.

### Pets Module
1. **View** — All pets are listed in the table. Use the search bar or filter dropdown to narrow results.
2. **Add Pet** — Click "Add Pet", fill in the form, and click Save.
3. **Edit Pet** — Select a row and click "Edit", update fields, and Save.
4. **Delete Pet** — Select a row and click "Delete". A confirmation dialog appears. Deleting a pet also removes its vaccination records and adoption applications.

### Adoptions Module
1. **Submit Application** — Choose a pet (must be Available) and an adopter, add optional notes, and click Submit.
2. **Approve** — Select a Pending application and click Approve. The pet's status changes to Adopted and all other pending applications for that pet are auto-rejected.
3. **Reject** — Select a Pending application and click Reject.

### Vaccinations Module
1. **Add Record** — Select a pet, enter vaccine name, date administered, and next due date.
2. **Edit / Delete** — Select a row to modify or remove a vaccination record.
3. Vaccinations due within the next 30 days are highlighted for quick attention.

### Reports Module
- Click **Refresh Reports** at any time to reload all charts from the latest database state.
- Charts auto-load when you navigate to the Reports page.

---

## 🌱 Sample Data

On first launch, PawPal automatically seeds the database with:

| Category | Count | Details |
|----------|-------|---------|
| Pets | 8 | Mix of dogs, cats, and rabbits in various statuses |
| Adopters | 3 | Alice Johnson, Bob Martinez, Carol Lee |
| Adoptions | 2 | Max → Alice (Approved), Daisy → Bob (Approved) |
| Vaccinations | 5 | Rabies, DHPP, FVRCP, Feline Leukemia records |

> [!TIP]
> Sample data is seeded only once — if you delete all pets and restart, it will seed again.

---

## 🧪 Testing

### Run all tests with pytest

```bash
python -m pytest tests/ -v
```

### Run tests directly with Python

```bash
python tests/test_database.py
```

### What is tested

| Test Class | Coverage |
|------------|----------|
| `TestPetOperations` | Add, edit, delete, search, filter pets |
| `TestAdopterOperations` | Add, edit, delete adopters; duplicate email handling |
| `TestAdoptionOperations` | Submit, approve, reject applications; prevent double adoption |
| `TestVaccinationOperations` | Add, edit, delete; upcoming vaccination window |
| `TestDashboardStats` | Empty DB zeros; correct counts after data insertion |

> [!NOTE]
> Tests use isolated temporary SQLite databases — your real data is never touched.

---

## ⚠️ Known Limitations

- **Single-user only** — No multi-user authentication or role-based access control.
- **No image upload UI** — Pet images can be stored as file paths in the database, but the image upload UI is not yet implemented.
- **No export feature** — Reports cannot be exported to PDF or CSV in the current version.
- **Windows-first** — The app is developed and tested on Windows. It should run on macOS and Linux, but `state='zoomed'` maximization may behave differently.
- **No network sync** — All data is stored locally; there is no cloud backup or sync mechanism.

---

## 👤 Credits & Authors

| Role | Name |
|------|------|
| Developer | Vansh |
| Framework | Python 3 + Tkinter |
| Charting | Matplotlib |
| Database | SQLite 3 (via Python `sqlite3` stdlib) |

---

*PawPal — because every pet deserves a loving home 🐾*
