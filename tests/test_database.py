"""
tests/test_database.py — Comprehensive unit tests for PawPal's database module.

Run with:
    python tests/test_database.py        (direct)
    python -m pytest tests/              (via pytest)
"""

import unittest
import os
import sys
import tempfile
import sqlite3
from datetime import date, timedelta

# Allow imports from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import database as db


# ---------------------------------------------------------------------------
# Test-database helper
# ---------------------------------------------------------------------------

def _use_temp_db(test_case_instance):
    """
    Point the database module at a fresh temporary file and initialise the
    schema.  Called from each test-class setUp().  Tears down in tearDown().
    """
    # Create a named temp file; we'll delete it manually in tearDown
    fd, path = tempfile.mkstemp(suffix=".db", prefix="pawpal_test_")
    os.close(fd)
    test_case_instance._temp_db_path = path

    # Monkey-patch the private path variables in the database module
    db._DB_PATH = path
    db._DB_DIR  = os.path.dirname(path)
    db.initialize_database()


def _restore_db():
    """Remove the monkey-patch by resetting to the real DB path."""
    real_dir  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database")
    real_path = os.path.join(real_dir, "pawpal.db")
    db._DB_DIR  = real_dir
    db._DB_PATH = real_path


# ===========================================================================
# 1.  Pet Operations
# ===========================================================================

class TestPetOperations(unittest.TestCase):
    """CRUD and search operations on the pets table."""

    def setUp(self):
        _use_temp_db(self)

    def tearDown(self):
        _restore_db()
        try:
            os.remove(self._temp_db_path)
        except OSError:
            pass

    # ── helpers ─────────────────────────────────────────────────────────────

    def _add_sample_pet(self, name="Buddy", species="Dog", status="Available"):
        return db.add_pet(
            name=name,
            species=species,
            breed="Mixed",
            age=2.0,
            gender="Male",
            description="A good boy.",
            status=status,
        )

    # ── tests ────────────────────────────────────────────────────────────────

    def test_add_pet(self):
        """Adding a pet should return a positive integer pet_id."""
        pet_id = self._add_sample_pet("Rex")
        self.assertIsInstance(pet_id, int)
        self.assertGreater(pet_id, 0)

        pet = db.get_pet_by_id(pet_id)
        self.assertIsNotNone(pet)
        self.assertEqual(pet["name"], "Rex")
        self.assertEqual(pet["species"], "Dog")
        self.assertEqual(pet["status"], "Available")

    def test_add_pet_missing_required(self):
        """
        Adding a pet without required fields (name or species) should raise an
        exception (sqlite3.Error or similar) rather than silently inserting a
        broken record.
        """
        with self.assertRaises(Exception):
            # name is NOT NULL in the schema
            db.add_pet(name=None, species="Dog")  # type: ignore

    def test_edit_pet(self):
        """Updating a pet should persist all changed fields."""
        pet_id = self._add_sample_pet("Luna", "Cat")
        result = db.update_pet(
            pet_id=pet_id,
            name="Luna Updated",
            species="Cat",
            breed="Siamese",
            age=3.0,
            gender="Female",
            description="Updated description.",
            status="Adopted",
        )
        self.assertTrue(result)

        pet = db.get_pet_by_id(pet_id)
        self.assertEqual(pet["name"], "Luna Updated")
        self.assertEqual(pet["breed"], "Siamese")
        self.assertAlmostEqual(pet["age"], 3.0)
        self.assertEqual(pet["status"], "Adopted")

    def test_delete_pet(self):
        """Deleting a pet should remove it from the database."""
        pet_id = self._add_sample_pet("Ghost")
        result = db.delete_pet(pet_id)
        self.assertTrue(result)

        pet = db.get_pet_by_id(pet_id)
        self.assertIsNone(pet)

    def test_delete_pet_nonexistent(self):
        """Deleting a non-existent pet_id should return True (no error)."""
        result = db.delete_pet(99999)
        self.assertTrue(result)  # No row affected, but no crash

    def test_search_pet_by_name(self):
        """search_pets should find a pet by partial name match."""
        self._add_sample_pet("Goldie", "Dog")
        self._add_sample_pet("Whiskers", "Cat")

        results = db.search_pets("Gold")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Goldie")

    def test_search_pet_by_species(self):
        """search_pets should find pets by species."""
        self._add_sample_pet("Fido", "Dog")
        self._add_sample_pet("Mittens", "Cat")

        results = db.search_pets("Dog")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Fido")

    def test_filter_by_species(self):
        """
        get_all_pets should return all pets; we can manually filter by species.
        """
        self._add_sample_pet("Dog1", "Dog")
        self._add_sample_pet("Dog2", "Dog")
        self._add_sample_pet("Cat1", "Cat")

        all_pets = db.get_all_pets()
        dogs = [p for p in all_pets if p["species"] == "Dog"]
        cats = [p for p in all_pets if p["species"] == "Cat"]

        self.assertEqual(len(dogs), 2)
        self.assertEqual(len(cats), 1)

    def test_filter_by_status(self):
        """get_pets_by_status should return only pets with that status."""
        self._add_sample_pet("Available1", status="Available")
        self._add_sample_pet("Available2", status="Available")
        self._add_sample_pet("Adopted1",   status="Adopted")

        available = db.get_pets_by_status("Available")
        adopted   = db.get_pets_by_status("Adopted")

        self.assertEqual(len(available), 2)
        self.assertEqual(len(adopted), 1)
        self.assertEqual(adopted[0]["name"], "Adopted1")

    def test_get_all_pets_empty(self):
        """get_all_pets on an empty DB returns an empty list."""
        self.assertEqual(db.get_all_pets(), [])

    def test_get_pet_by_id_not_found(self):
        """get_pet_by_id with a missing ID returns None."""
        self.assertIsNone(db.get_pet_by_id(12345))


# ===========================================================================
# 2.  Adopter Operations
# ===========================================================================

class TestAdopterOperations(unittest.TestCase):
    """CRUD operations on the adopters table."""

    def setUp(self):
        _use_temp_db(self)

    def tearDown(self):
        _restore_db()
        try:
            os.remove(self._temp_db_path)
        except OSError:
            pass

    def _add_sample_adopter(self, name="Alice", email="alice@example.com"):
        return db.add_adopter(
            full_name=name,
            phone="555-0001",
            email=email,
            address="123 Main St",
        )

    def test_add_adopter(self):
        """Adding an adopter should return a positive adopter_id."""
        adopter_id = self._add_sample_adopter()
        self.assertIsInstance(adopter_id, int)
        self.assertGreater(adopter_id, 0)

        adopter = db.get_adopter_by_id(adopter_id)
        self.assertIsNotNone(adopter)
        self.assertEqual(adopter["full_name"], "Alice")
        self.assertEqual(adopter["email"], "alice@example.com")

    def test_edit_adopter(self):
        """Updating an adopter should persist the new values."""
        adopter_id = self._add_sample_adopter("Bob", "bob@example.com")

        result = db.update_adopter(
            adopter_id=adopter_id,
            full_name="Robert",
            phone="555-9999",
            email="robert@example.com",
            address="456 Oak Ave",
        )
        self.assertTrue(result)

        adopter = db.get_adopter_by_id(adopter_id)
        self.assertEqual(adopter["full_name"], "Robert")
        self.assertEqual(adopter["phone"], "555-9999")
        self.assertEqual(adopter["email"], "robert@example.com")

    def test_delete_adopter(self):
        """Deleting an adopter should remove the record."""
        adopter_id = self._add_sample_adopter("Carol", "carol@example.com")
        result = db.delete_adopter(adopter_id)
        self.assertTrue(result)

        adopter = db.get_adopter_by_id(adopter_id)
        self.assertIsNone(adopter)

    def test_duplicate_email(self):
        """
        Inserting two adopters with the same email (UNIQUE constraint) should
        raise a sqlite3.IntegrityError — the database handles this gracefully
        by raising rather than silently overwriting.
        """
        self._add_sample_adopter("Alice", "shared@example.com")
        with self.assertRaises(Exception):
            self._add_sample_adopter("Alice2", "shared@example.com")

    def test_get_all_adopters_empty(self):
        """get_all_adopters on an empty DB returns an empty list."""
        self.assertEqual(db.get_all_adopters(), [])

    def test_search_adopters(self):
        """search_adopters should find by partial name match."""
        self._add_sample_adopter("Diana Prince", "diana@example.com")
        self._add_sample_adopter("Clark Kent", "clark@example.com")

        results = db.search_adopters("Diana")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["full_name"], "Diana Prince")


# ===========================================================================
# 3.  Adoption Operations
# ===========================================================================

class TestAdoptionOperations(unittest.TestCase):
    """Adoption application workflow tests."""

    def setUp(self):
        _use_temp_db(self)
        # Pre-create one pet and one adopter for use in tests
        self.pet_id = db.add_pet(
            name="TestPet", species="Dog", breed="Lab", age=1.0,
            gender="Male", status="Available"
        )
        self.adopter_id = db.add_adopter(
            full_name="Test Adopter",
            phone="555-1234",
            email="adopter@test.com",
            address="789 Test Lane",
        )

    def tearDown(self):
        _restore_db()
        try:
            os.remove(self._temp_db_path)
        except OSError:
            pass

    def test_submit_application(self):
        """Submitting an application should return a positive application_id."""
        app_id = db.add_application(
            pet_id=self.pet_id,
            adopter_id=self.adopter_id,
            notes="I would love to adopt this dog.",
        )
        self.assertIsInstance(app_id, int)
        self.assertGreater(app_id, 0)

        apps = db.get_all_applications()
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["status"], "Pending")
        self.assertEqual(apps[0]["pet_id"], self.pet_id)

    def test_approve_application(self):
        """
        Approving an application should:
        - Set application status to 'Approved'
        - Change the pet's status to 'Adopted'
        """
        app_id = db.add_application(self.pet_id, self.adopter_id, "Great home!")
        result = db.approve_application(app_id)
        self.assertTrue(result)

        apps = db.get_all_applications()
        self.assertEqual(apps[0]["status"], "Approved")

        pet = db.get_pet_by_id(self.pet_id)
        self.assertEqual(pet["status"], "Adopted")

    def test_reject_application(self):
        """Rejecting an application should set its status to 'Rejected'."""
        app_id = db.add_application(self.pet_id, self.adopter_id)
        result = db.reject_application(app_id, notes="Insufficient space.")
        self.assertTrue(result)

        apps = db.get_all_applications()
        self.assertEqual(apps[0]["status"], "Rejected")
        # Pet should still be Available
        pet = db.get_pet_by_id(self.pet_id)
        self.assertEqual(pet["status"], "Available")

    def test_prevent_double_adoption(self):
        """
        After a pet is adopted, approving a second application for the same
        pet should still execute (the function doesn't block it at the DB
        layer), but the first approval makes the pet Adopted and the second
        application would have been auto-rejected.  We verify via
        get_applications_by_pet.
        """
        # Add a second adopter
        adopter2_id = db.add_adopter(
            full_name="Second Adopter",
            email="second@test.com",
        )

        app1_id = db.add_application(self.pet_id, self.adopter_id, "First!")
        app2_id = db.add_application(self.pet_id, adopter2_id, "Second!")

        # Approve first application — this should auto-reject app2
        db.approve_application(app1_id)

        apps = db.get_applications_by_pet(self.pet_id)
        statuses = {a["application_id"]: a["status"] for a in apps}

        self.assertEqual(statuses[app1_id], "Approved")
        self.assertEqual(statuses[app2_id], "Rejected")  # auto-rejected by approve_application

    def test_get_adoption_history(self):
        """get_adoption_history should return only approved applications."""
        app_id = db.add_application(self.pet_id, self.adopter_id)
        db.approve_application(app_id)

        # Add a second pet+application that stays pending
        pet2_id = db.add_pet("Pet2", "Cat", status="Available")
        db.add_application(pet2_id, self.adopter_id)

        history = db.get_adoption_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["application_id"], app_id)


# ===========================================================================
# 4.  Vaccination Operations
# ===========================================================================

class TestVaccinationOperations(unittest.TestCase):
    """CRUD operations on the vaccinations table."""

    def setUp(self):
        _use_temp_db(self)
        self.pet_id = db.add_pet(
            name="VaccPet", species="Cat", breed="Tabby", age=2.0,
            gender="Female", status="Available"
        )

    def tearDown(self):
        _restore_db()
        try:
            os.remove(self._temp_db_path)
        except OSError:
            pass

    def _today(self):
        return date.today().isoformat()

    def _days_from_now(self, n):
        return (date.today() + timedelta(days=n)).isoformat()

    def test_add_vaccination(self):
        """Adding a vaccination should return a positive vaccination_id."""
        vacc_id = db.add_vaccination(
            pet_id=self.pet_id,
            vaccine_name="Rabies",
            vaccination_date=self._today(),
            next_due_date=self._days_from_now(365),
            notes="Annual booster",
        )
        self.assertIsInstance(vacc_id, int)
        self.assertGreater(vacc_id, 0)

        vaccs = db.get_vaccinations_by_pet(self.pet_id)
        self.assertEqual(len(vaccs), 1)
        self.assertEqual(vaccs[0]["vaccine_name"], "Rabies")

    def test_edit_vaccination(self):
        """Updating a vaccination should persist the new vaccine name and dates."""
        vacc_id = db.add_vaccination(
            pet_id=self.pet_id,
            vaccine_name="FVRCP",
            vaccination_date=self._today(),
            next_due_date=self._days_from_now(180),
        )
        result = db.update_vaccination(
            vaccination_id=vacc_id,
            vaccine_name="FVRCP-Updated",
            vaccination_date=self._today(),
            next_due_date=self._days_from_now(365),
            notes="Updated notes",
        )
        self.assertTrue(result)

        vaccs = db.get_vaccinations_by_pet(self.pet_id)
        self.assertEqual(vaccs[0]["vaccine_name"], "FVRCP-Updated")
        self.assertEqual(vaccs[0]["notes"], "Updated notes")

    def test_delete_vaccination(self):
        """Deleting a vaccination should remove the record."""
        vacc_id = db.add_vaccination(
            pet_id=self.pet_id,
            vaccine_name="DHPP",
            vaccination_date=self._today(),
        )
        result = db.delete_vaccination(vacc_id)
        self.assertTrue(result)

        vaccs = db.get_vaccinations_by_pet(self.pet_id)
        self.assertEqual(len(vaccs), 0)

    def test_upcoming_vaccinations(self):
        """get_upcoming_vaccinations should return only future records within the window."""
        # Due in 10 days — should be in upcoming (30-day window)
        db.add_vaccination(
            pet_id=self.pet_id,
            vaccine_name="Upcoming1",
            vaccination_date=self._today(),
            next_due_date=self._days_from_now(10),
        )
        # Due in 60 days — outside 30-day window
        db.add_vaccination(
            pet_id=self.pet_id,
            vaccine_name="Future",
            vaccination_date=self._today(),
            next_due_date=self._days_from_now(60),
        )
        # Due in the past — should not appear
        db.add_vaccination(
            pet_id=self.pet_id,
            vaccine_name="Overdue",
            vaccination_date=self._days_from_now(-30),
            next_due_date=self._days_from_now(-5),
        )

        upcoming = db.get_upcoming_vaccinations(days=30)
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0]["vaccine_name"], "Upcoming1")

    def test_get_all_vaccinations_joined(self):
        """get_all_vaccinations should include the pet_name column."""
        db.add_vaccination(
            pet_id=self.pet_id,
            vaccine_name="Leukemia",
            vaccination_date=self._today(),
        )
        all_v = db.get_all_vaccinations()
        self.assertEqual(len(all_v), 1)
        self.assertIn("pet_name", all_v[0].keys())
        self.assertEqual(all_v[0]["pet_name"], "VaccPet")


# ===========================================================================
# 5.  Dashboard Stats
# ===========================================================================

class TestDashboardStats(unittest.TestCase):
    """get_dashboard_stats() aggregation tests."""

    def setUp(self):
        _use_temp_db(self)

    def tearDown(self):
        _restore_db()
        try:
            os.remove(self._temp_db_path)
        except OSError:
            pass

    def test_stats_empty_db(self):
        """On a freshly initialised DB all numeric stats should be 0."""
        stats = db.get_dashboard_stats()

        self.assertEqual(stats["total_pets"], 0)
        self.assertEqual(stats["available_pets"], 0)
        self.assertEqual(stats["adopted_pets"], 0)
        self.assertEqual(stats["pending_applications"], 0)
        self.assertEqual(stats["recent_pets"], [])
        self.assertEqual(stats["species_distribution"], {})

    def test_stats_with_data(self):
        """
        After adding records the stats should reflect the actual counts.
        """
        # Add pets
        pet1 = db.add_pet("Spot",   "Dog", status="Available")
        pet2 = db.add_pet("Whisky", "Dog", status="Adopted")
        pet3 = db.add_pet("Nemo",   "Fish", status="Available")

        # Add an adopter and a pending application
        adopter_id = db.add_adopter("Stats Tester", email="stats@test.com")
        db.add_application(pet1, adopter_id, "Looking forward to it!")

        stats = db.get_dashboard_stats()

        self.assertEqual(stats["total_pets"], 3)
        self.assertEqual(stats["available_pets"], 2)
        self.assertEqual(stats["adopted_pets"], 1)
        self.assertEqual(stats["pending_applications"], 1)

        # Species distribution
        self.assertIn("Dog", stats["species_distribution"])
        self.assertEqual(stats["species_distribution"]["Dog"], 2)
        self.assertIn("Fish", stats["species_distribution"])
        self.assertEqual(stats["species_distribution"]["Fish"], 1)

    def test_stats_recent_pets_limit(self):
        """recent_pets should contain at most 5 entries."""
        for i in range(8):
            db.add_pet(f"Pet{i}", "Dog")

        stats = db.get_dashboard_stats()
        self.assertLessEqual(len(stats["recent_pets"]), 5)

    def test_stats_monthly_adoptions_length(self):
        """monthly_adoptions should always return exactly 6 entries."""
        stats = db.get_dashboard_stats()
        self.assertEqual(len(stats["monthly_adoptions"]), 6)
        for entry in stats["monthly_adoptions"]:
            self.assertIn("month", entry)
            self.assertIn("count", entry)

    def test_stats_after_approval(self):
        """
        Approving an application should decrease pending count and correctly
        reflect in adopted count if the pet's status is updated.
        """
        pet_id = db.add_pet("Approved Pet", "Cat", status="Available")
        adopter_id = db.add_adopter("Approver", email="approver@test.com")
        app_id = db.add_application(pet_id, adopter_id)

        # Before approval
        before = db.get_dashboard_stats()
        self.assertEqual(before["pending_applications"], 1)
        self.assertEqual(before["adopted_pets"], 0)

        db.approve_application(app_id)

        # After approval
        after = db.get_dashboard_stats()
        self.assertEqual(after["pending_applications"], 0)
        self.assertEqual(after["adopted_pets"], 1)
        self.assertEqual(after["available_pets"], 0)


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
