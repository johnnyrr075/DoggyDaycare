"""Database utilities for the Doggy Daycare management platform."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = 1


def dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict:
    """Return rows as dictionaries rather than tuples."""

    return {description[0]: row[idx] for idx, description in enumerate(cursor.description)}


def get_connection(path: str | Path) -> sqlite3.Connection:
    """Return a SQLite connection with sensible defaults."""

    conn = sqlite3.connect(path)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def initialize_database(conn: sqlite3.Connection) -> None:
    """Create the database schema if it does not yet exist."""

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            timezone TEXT DEFAULT 'Australia/Sydney',
            address TEXT,
            suburb TEXT,
            state TEXT,
            postcode TEXT,
            capacity INTEGER DEFAULT 0,
            base_daycare_rate REAL DEFAULT 0,
            second_pet_discount REAL DEFAULT 0,
            gst_registered INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            api_key TEXT UNIQUE,
            location_id INTEGER,
            name TEXT,
            phone TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(location_id) REFERENCES locations(id)
        );

        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            suburb TEXT,
            state TEXT,
            postcode TEXT,
            emergency_contact_name TEXT,
            emergency_contact_phone TEXT,
            marketing_opt_in INTEGER DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            breed TEXT,
            birth_date TEXT,
            gender TEXT,
            colour TEXT,
            medical_notes TEXT,
            feeding_instructions TEXT,
            behaviour_flags TEXT,
            allergies TEXT,
            photo_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            archived INTEGER DEFAULT 0,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS pet_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            note TEXT NOT NULL,
            flag_type TEXT,
            severity TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(pet_id) REFERENCES pets(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS vaccination_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            vaccine_name TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            document_url TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(pet_id) REFERENCES pets(id)
        );

        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            default_duration_minutes INTEGER DEFAULT 0,
            price REAL NOT NULL,
            gst_applicable INTEGER DEFAULT 1,
            location_id INTEGER,
            allow_multiple_pets INTEGER DEFAULT 1,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(location_id) REFERENCES locations(id)
        );

        CREATE TABLE IF NOT EXISTS daycare_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            location_id INTEGER,
            total_credits INTEGER NOT NULL,
            price REAL NOT NULL,
            gst_inclusive INTEGER DEFAULT 1,
            valid_days INTEGER,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(location_id) REFERENCES locations(id)
        );

        CREATE TABLE IF NOT EXISTS client_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            remaining_credits INTEGER NOT NULL,
            purchase_date TEXT NOT NULL,
            expiry_date TEXT,
            metadata TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(package_id) REFERENCES daycare_packages(id)
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'reserved',
            notes TEXT,
            created_by INTEGER,
            recurrence_rule TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(location_id) REFERENCES locations(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS booking_pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            pet_id INTEGER NOT NULL,
            package_id INTEGER,
            price REAL NOT NULL,
            gst_applicable INTEGER DEFAULT 1,
            status TEXT DEFAULT 'booked',
            FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
            FOREIGN KEY(pet_id) REFERENCES pets(id),
            FOREIGN KEY(package_id) REFERENCES client_packages(id)
        );

        CREATE TABLE IF NOT EXISTS booking_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            price REAL NOT NULL,
            gst_applicable INTEGER DEFAULT 1,
            FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
            FOREIGN KEY(service_id) REFERENCES services(id)
        );

        CREATE TABLE IF NOT EXISTS waitlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            pet_id INTEGER NOT NULL,
            requested_start TEXT NOT NULL,
            requested_end TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(location_id) REFERENCES locations(id),
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(pet_id) REFERENCES pets(id)
        );

        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_pet_id INTEGER NOT NULL,
            check_in_time TEXT,
            check_out_time TEXT,
            staff_user_id INTEGER,
            waiver_signed INTEGER DEFAULT 0,
            health_check_passed INTEGER DEFAULT 1,
            notes TEXT,
            FOREIGN KEY(booking_pet_id) REFERENCES booking_pets(id),
            FOREIGN KEY(staff_user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            client_id INTEGER NOT NULL,
            invoice_number TEXT UNIQUE,
            issue_date TEXT NOT NULL,
            due_date TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            subtotal REAL NOT NULL,
            gst_amount REAL NOT NULL,
            total REAL NOT NULL,
            balance_due REAL NOT NULL,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(booking_id) REFERENCES bookings(id),
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS invoice_line_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            gst_rate REAL NOT NULL,
            total REAL NOT NULL,
            metadata TEXT,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            method TEXT NOT NULL,
            payment_date TEXT NOT NULL,
            reference TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            channel TEXT NOT NULL,
            template_code TEXT,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'queued',
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            direction TEXT NOT NULL,
            channel TEXT NOT NULL,
            content TEXT NOT NULL,
            staff_user_id INTEGER,
            related_booking_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(staff_user_id) REFERENCES users(id),
            FOREIGN KEY(related_booking_id) REFERENCES bookings(id)
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            content TEXT,
            requires_signature INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS document_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            due_date TEXT,
            signed_at TEXT,
            captured_data TEXT,
            FOREIGN KEY(document_id) REFERENCES documents(id),
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS pet_activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            booking_id INTEGER,
            activity_type TEXT NOT NULL,
            details TEXT,
            logged_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(pet_id) REFERENCES pets(id),
            FOREIGN KEY(booking_id) REFERENCES bookings(id),
            FOREIGN KEY(logged_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE,
            quantity INTEGER NOT NULL,
            unit_cost REAL,
            unit_price REAL,
            taxable INTEGER DEFAULT 1,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS inventory_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            quantity_change INTEGER NOT NULL,
            reason TEXT NOT NULL,
            staff_user_id INTEGER,
            related_invoice_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(item_id) REFERENCES inventory_items(id),
            FOREIGN KEY(staff_user_id) REFERENCES users(id),
            FOREIGN KEY(related_invoice_id) REFERENCES invoices(id)
        );

        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            position TEXT,
            hourly_rate REAL,
            started_on TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS staff_shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            location_id INTEGER,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(id),
            FOREIGN KEY(location_id) REFERENCES locations(id)
        );

        CREATE TABLE IF NOT EXISTS time_clock_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            clock_in TEXT NOT NULL,
            clock_out TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );

        CREATE TABLE IF NOT EXISTS recurring_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            rule TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(location_id) REFERENCES locations(id),
            FOREIGN KEY(client_id) REFERENCES clients(id)
        );
        """
    )

    set_metadata(conn, "schema_version", SCHEMA_VERSION)


def set_metadata(conn: sqlite3.Connection, key: str, value: int | str | dict | list) -> None:
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    conn.execute(
        "INSERT INTO metadata(key, value) VALUES (?, ?)\n         ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()


def get_metadata(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def execute_many(conn: sqlite3.Connection, sql: str, parameters: Iterable[tuple]) -> None:
    conn.executemany(sql, parameters)
    conn.commit()
