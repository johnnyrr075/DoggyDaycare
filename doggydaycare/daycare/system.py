"""Core orchestration logic for the Doggy Daycare platform."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import secrets
import sqlite3
from collections import defaultdict
from typing import Any, Iterable, Sequence

from .database import get_connection, initialize_database

GST_RATE = 0.10


class AuthorizationError(RuntimeError):
    """Raised when a user action is not permitted."""


class ValidationError(RuntimeError):
    """Raised when incoming data fails validation."""


class DaycareSystem:
    """High level façade that exposes application level behaviours."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.conn = get_connection(db_path)
        initialize_database(self.conn)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 390000)
        return f"pbkdf2_sha256${salt}${digest.hex()}"

    def _verify_password(self, stored: str, provided: str) -> bool:
        algorithm, salt, hex_digest = stored.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", provided.encode(), salt.encode(), 390000)
        return secrets.compare_digest(candidate.hex(), hex_digest)

    def _require_role(self, api_key: str, allowed: Sequence[str]) -> dict:
        user = self.conn.execute(
            "SELECT * FROM users WHERE api_key = ? AND is_active = 1", (api_key,)
        ).fetchone()
        if not user or user["role"] not in allowed:
            raise AuthorizationError("User does not have permission to perform this action")
        return user

    def _get_next_sequence(self, name: str) -> int:
        row = self.conn.execute(
            "SELECT value FROM metadata WHERE key = ?", (f"seq_{name}",)
        ).fetchone()
        current = int(row["value"]) if row else 0
        next_value = current + 1
        self.conn.execute(
            "INSERT INTO metadata(key, value) VALUES(?, ?)\n             ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (f"seq_{name}", str(next_value)),
        )
        self.conn.commit()
        return next_value

    # ------------------------------------------------------------------
    # Authentication & users
    # ------------------------------------------------------------------
    def register_user(
        self,
        *,
        email: str,
        password: str,
        role: str,
        name: str | None = None,
        phone: str | None = None,
        location_id: int | None = None,
    ) -> dict:
        password_hash = self._hash_password(password)
        api_key = secrets.token_hex(16)
        cur = self.conn.execute(
            """
            INSERT INTO users(email, password_hash, role, api_key, name, phone, location_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (email.lower(), password_hash, role, api_key, name, phone, location_id),
        )
        self.conn.commit()
        return self.get_user(cur.lastrowid)

    def get_user(self, user_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise ValidationError("User not found")
        return row

    def login(self, *, email: str, password: str) -> dict:
        row = self.conn.execute(
            "SELECT * FROM users WHERE email = ? AND is_active = 1", (email.lower(),)
        ).fetchone()
        if not row or not self._verify_password(row["password_hash"], password):
            raise AuthorizationError("Invalid credentials")
        return {"user_id": row["id"], "api_key": row["api_key"], "role": row["role"]}

 codex/create-dog-daycare-management-system-yeinmr
    def list_users(self, *, location_id: int | None = None) -> list[dict]:
        """Return active users, optionally filtered by location."""

        params: list[Any] = []
        where = " WHERE is_active = 1"
        if location_id is not None:
            where += " AND (location_id = ? OR location_id IS NULL)"
            params.append(location_id)
        return self.conn.execute(
            "SELECT * FROM users" + where + " ORDER BY role, name",
            params,
        ).fetchall()


 main
    # ------------------------------------------------------------------
    # Locations & clients
    # ------------------------------------------------------------------
    def create_location(
        self,
        *,
        name: str,
        capacity: int,
        base_daycare_rate: float,
        second_pet_discount: float = 0,
        timezone: str = "Australia/Sydney",
        address: str | None = None,
        suburb: str | None = None,
        state: str | None = None,
        postcode: str | None = None,
        gst_registered: bool = True,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO locations(
                name, capacity, base_daycare_rate, second_pet_discount, timezone,
                address, suburb, state, postcode, gst_registered
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                capacity,
                base_daycare_rate,
                second_pet_discount,
                timezone,
                address,
                suburb,
                state,
                postcode,
                int(gst_registered),
            ),
        )
        self.conn.commit()
        return self.get_location(cur.lastrowid)

    def get_location(self, location_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM locations WHERE id = ?", (location_id,)
        ).fetchone()
        if not row:
            raise ValidationError("Location not found")
        return row

 codex/create-dog-daycare-management-system-yeinmr
    def list_locations(self) -> list[dict]:
        """Return all locations ordered by name."""

        return self.conn.execute(
            "SELECT * FROM locations ORDER BY name"
        ).fetchall()


 main
    def register_client(
        self,
        *,
        first_name: str,
        last_name: str,
        phone: str,
        email: str,
        address: str | None = None,
        suburb: str | None = None,
        state: str | None = None,
        postcode: str | None = None,
        emergency_contact_name: str | None = None,
        emergency_contact_phone: str | None = None,
        marketing_opt_in: bool = False,
        notes: str | None = None,
        user_id: int | None = None,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO clients(
                user_id, first_name, last_name, phone, email, address, suburb, state, postcode,
                emergency_contact_name, emergency_contact_phone, marketing_opt_in, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                first_name,
                last_name,
                phone,
                email.lower(),
                address,
                suburb,
                state,
                postcode,
                emergency_contact_name,
                emergency_contact_phone,
                int(marketing_opt_in),
                notes,
            ),
        )
        self.conn.commit()
        return self.get_client(cur.lastrowid)

    def get_client(self, client_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        if not row:
            raise ValidationError("Client not found")
        return row

 codex/create-dog-daycare-management-system-yeinmr
    def list_clients(self) -> list[dict]:
        """Return all clients ordered alphabetically."""

        return self.conn.execute(
            """
            SELECT clients.*,
                   COALESCE(users.email, clients.email) AS login_email
            FROM clients
            LEFT JOIN users ON users.id = clients.user_id
            ORDER BY last_name, first_name
            """
        ).fetchall()


 main
    # ------------------------------------------------------------------
    # Pets & health records
    # ------------------------------------------------------------------
    def add_pet(
        self,
        *,
        client_id: int,
        name: str,
        breed: str | None = None,
        birth_date: str | None = None,
        gender: str | None = None,
        colour: str | None = None,
        medical_notes: str | None = None,
        feeding_instructions: str | None = None,
        behaviour_flags: str | None = None,
        allergies: str | None = None,
        photo_url: str | None = None,
    ) -> dict:
        self.get_client(client_id)
        cur = self.conn.execute(
            """
            INSERT INTO pets(
                client_id, name, breed, birth_date, gender, colour, medical_notes,
                feeding_instructions, behaviour_flags, allergies, photo_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                name,
                breed,
                birth_date,
                gender,
                colour,
                medical_notes,
                feeding_instructions,
                behaviour_flags,
                allergies,
                photo_url,
            ),
        )
        self.conn.commit()
        return self.get_pet(cur.lastrowid)

    def get_pet(self, pet_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM pets WHERE id = ?", (pet_id,)).fetchone()
        if not row:
            raise ValidationError("Pet not found")
        return row

 codex/create-dog-daycare-management-system-yeinmr
    def list_pets(self, *, client_id: int | None = None, include_archived: bool = False) -> list[dict]:
        """Return pets, optionally filtered by client."""

        conditions: list[str] = []
        params: list[Any] = []
        if client_id is not None:
            conditions.append("pets.client_id = ?")
            params.append(client_id)
        if not include_archived:
            conditions.append("pets.archived = 0")
        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
        query = (
            """
            SELECT pets.*, clients.first_name || ' ' || clients.last_name AS owner_name
            FROM pets
            JOIN clients ON clients.id = pets.client_id
            {where}
            ORDER BY pets.name
            """.format(where=where_clause)
        )
        return self.conn.execute(query, params).fetchall()

    def list_vaccinations(self, *, pet_id: int) -> list[dict]:
        """Return vaccination records for a pet."""

        self.get_pet(pet_id)
        return self.conn.execute(
            """
            SELECT * FROM vaccination_records
            WHERE pet_id = ?
            ORDER BY expiry_date DESC
            """,
            (pet_id,),
        ).fetchall()


 main
    def record_vaccination(
        self,
        *,
        pet_id: int,
        vaccine_name: str,
        expiry_date: str,
        document_url: str | None = None,
        notes: str | None = None,
    ) -> dict:
        self.get_pet(pet_id)
        cur = self.conn.execute(
            """
            INSERT INTO vaccination_records(pet_id, vaccine_name, expiry_date, document_url, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (pet_id, vaccine_name, expiry_date, document_url, notes),
        )
        self.conn.commit()
        return self.get_vaccination(cur.lastrowid)

    def get_vaccination(self, record_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM vaccination_records WHERE id = ?", (record_id,)
        ).fetchone()
        if not row:
            raise ValidationError("Vaccination record not found")
        return row

    def add_pet_note(
        self,
        *,
        pet_id: int,
        note: str,
        flag_type: str | None = None,
        severity: str | None = None,
        created_by: int | None = None,
    ) -> dict:
        self.get_pet(pet_id)
        cur = self.conn.execute(
            """
            INSERT INTO pet_notes(pet_id, note, flag_type, severity, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (pet_id, note, flag_type, severity, created_by),
        )
        self.conn.commit()
 codex/create-dog-daycare-management-system-yeinmr
        return self.conn.execute(
            "SELECT * FROM pet_notes WHERE id = ?", (cur.lastrowid,)
        ).fetchone()

    def list_pet_notes(self, *, pet_id: int) -> list[dict]:
        """Return behavioural and care notes for a pet."""

        self.get_pet(pet_id)
        return self.conn.execute(
            """
            SELECT pet_notes.*, users.name AS staff_name
            FROM pet_notes
            LEFT JOIN users ON users.id = pet_notes.created_by
            WHERE pet_notes.pet_id = ?
            ORDER BY pet_notes.created_at DESC
            """,
            (pet_id,),
        ).fetchall()

        return self.conn.execute("SELECT * FROM pet_notes WHERE id = ?", (cur.lastrowid,)).fetchone()
 main

    # ------------------------------------------------------------------
    # Services, packages, inventory
    # ------------------------------------------------------------------
    def create_service(
        self,
        *,
        name: str,
        price: float,
        description: str | None = None,
        default_duration_minutes: int = 0,
        gst_applicable: bool = True,
        location_id: int | None = None,
        allow_multiple_pets: bool = True,
        metadata: dict | None = None,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO services(
                name, price, description, default_duration_minutes, gst_applicable,
                location_id, allow_multiple_pets, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                price,
                description,
                default_duration_minutes,
                int(gst_applicable),
                location_id,
                int(allow_multiple_pets),
                json.dumps(metadata or {}),
            ),
        )
        self.conn.commit()
        return self.get_service(cur.lastrowid)

    def get_service(self, service_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM services WHERE id = ?", (service_id,)).fetchone()
        if not row:
            raise ValidationError("Service not found")
        return row

 codex/create-dog-daycare-management-system-yeinmr
    def list_services(self, *, location_id: int | None = None) -> list[dict]:
        """Return services available for a location."""

        params: list[Any] = []
        where = ""
        if location_id is not None:
            where = " WHERE location_id IS NULL OR location_id = ?"
            params.append(location_id)
        return self.conn.execute(
            "SELECT * FROM services" + where + " ORDER BY name",
            params,
        ).fetchall()


 main
    def create_daycare_package(
        self,
        *,
        name: str,
        description: str,
        location_id: int | None,
        total_credits: int,
        price: float,
        gst_inclusive: bool = True,
        valid_days: int | None = None,
        metadata: dict | None = None,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO daycare_packages(
                name, description, location_id, total_credits, price, gst_inclusive,
                valid_days, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                description,
                location_id,
                total_credits,
                price,
                int(gst_inclusive),
                valid_days,
                json.dumps(metadata or {}),
            ),
        )
        self.conn.commit()
        return self.get_package(cur.lastrowid)

    def get_package(self, package_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM daycare_packages WHERE id = ?", (package_id,)
        ).fetchone()
        if not row:
            raise ValidationError("Package not found")
        return row

 codex/create-dog-daycare-management-system-yeinmr
    def list_packages(self, *, location_id: int | None = None) -> list[dict]:
        """Return daycare packages, optionally filtered by location."""

        params: list[Any] = []
        where = ""
        if location_id is not None:
            where = " WHERE location_id IS NULL OR location_id = ?"
            params.append(location_id)
        return self.conn.execute(
            "SELECT * FROM daycare_packages" + where + " ORDER BY name",
            params,
        ).fetchall()


 main
    def sell_package(
        self,
        *,
        client_id: int,
        package_id: int,
        purchase_date: str,
        expiry_date: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        package = self.get_package(package_id)
        cur = self.conn.execute(
            """
            INSERT INTO client_packages(client_id, package_id, remaining_credits, purchase_date, expiry_date, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                package_id,
                package["total_credits"],
                purchase_date,
                expiry_date,
                json.dumps(metadata or {}),
            ),
        )
        self.conn.commit()
        return self.get_client_package(cur.lastrowid)

    def get_client_package(self, client_package_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM client_packages WHERE id = ?", (client_package_id,)
        ).fetchone()
        if not row:
            raise ValidationError("Client package not found")
        return row

 codex/create-dog-daycare-management-system-yeinmr
    def list_client_packages(self, *, client_id: int) -> list[dict]:
        """Return packages owned by a client."""

        self.get_client(client_id)
        return self.conn.execute(
            """
            SELECT client_packages.*, daycare_packages.name AS package_name,
                   daycare_packages.total_credits
            FROM client_packages
            JOIN daycare_packages ON daycare_packages.id = client_packages.package_id
            WHERE client_packages.client_id = ?
            ORDER BY client_packages.purchase_date DESC
            """,
            (client_id,),
        ).fetchall()


 main
    def adjust_client_package(self, client_package_id: int, delta: int) -> dict:
        package = self.get_client_package(client_package_id)
        new_balance = package["remaining_credits"] + delta
        if new_balance < 0:
            raise ValidationError("Package does not have enough credits")
        self.conn.execute(
            "UPDATE client_packages SET remaining_credits = ? WHERE id = ?",
            (new_balance, client_package_id),
        )
        self.conn.commit()
        package["remaining_credits"] = new_balance
        return package

    def create_inventory_item(
        self,
        *,
        name: str,
        sku: str,
        quantity: int,
        unit_cost: float,
        unit_price: float,
        taxable: bool = True,
        metadata: dict | None = None,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO inventory_items(name, sku, quantity, unit_cost, unit_price, taxable, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                sku,
                quantity,
                unit_cost,
                unit_price,
                int(taxable),
                json.dumps(metadata or {}),
            ),
        )
        self.conn.commit()
        return self.get_inventory_item(cur.lastrowid)

    def get_inventory_item(self, item_id: int) -> dict:
        row = self.conn.execute(
            "SELECT * FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            raise ValidationError("Inventory item not found")
        return row

    def adjust_inventory(
        self,
        *,
        item_id: int,
        quantity_change: int,
        reason: str,
        staff_user_id: int | None = None,
        related_invoice_id: int | None = None,
    ) -> dict:
        item = self.get_inventory_item(item_id)
        new_quantity = item["quantity"] + quantity_change
        if new_quantity < 0:
            raise ValidationError("Inventory cannot be negative")
        self.conn.execute(
            "UPDATE inventory_items SET quantity = ? WHERE id = ?",
            (new_quantity, item_id),
        )
        self.conn.execute(
            """
            INSERT INTO inventory_transactions(item_id, quantity_change, reason, staff_user_id, related_invoice_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (item_id, quantity_change, reason, staff_user_id, related_invoice_id),
        )
        self.conn.commit()
        item["quantity"] = new_quantity
        return item

    # ------------------------------------------------------------------
    # Booking lifecycle
    # ------------------------------------------------------------------
    def _check_vaccination_valid(self, pet_id: int, reference_date: dt.datetime) -> None:
        row = self.conn.execute(
            """
            SELECT MAX(expiry_date) AS expiry
            FROM vaccination_records
            WHERE pet_id = ?
            """,
            (pet_id,),
        ).fetchone()
        if not row or not row["expiry"]:
            raise ValidationError("Pet is missing vaccination records")
        expiry = dt.datetime.fromisoformat(row["expiry"])
        if expiry < reference_date:
            raise ValidationError("Pet has expired vaccinations")

    def _count_pets_booked(
        self, *, location_id: int, start_time: dt.datetime, end_time: dt.datetime
    ) -> int:
        row = self.conn.execute(
            """
            SELECT COUNT(booking_pets.id) AS total
            FROM bookings
            JOIN booking_pets ON booking_pets.booking_id = bookings.id
            WHERE bookings.location_id = ?
              AND bookings.status IN ('reserved', 'confirmed', 'checked_in')
              AND NOT (
                    bookings.end_time <= ?
                    OR bookings.start_time >= ?
              )
            """,
            (location_id, start_time.isoformat(), end_time.isoformat()),
        ).fetchone()
        return row["total"] if row else 0

    def _create_invoice_for_booking(
        self,
        *,
        booking_id: int,
        client_id: int,
        pet_prices: list[tuple[str, float, bool]],
        service_rows: list[dict],
        issue_date: dt.date,
        deposit_amount: float = 0.0,
    ) -> dict:
        subtotal = sum(price for _, price, _ in pet_prices) + sum(
            row["price"] * row["quantity"] for row in service_rows
        )
        gstable_amount = sum(price for _, price, taxable in pet_prices if taxable) + sum(
            row["price"] * row["quantity"] for row in service_rows if row["gst_applicable"]
        )
        gst_amount = round(gstable_amount * GST_RATE, 2)
        total = round(subtotal + gst_amount, 2)
        balance = total
        invoice_number = self._generate_invoice_number(issue_date)
        cur = self.conn.execute(
            """
            INSERT INTO invoices(
                booking_id, client_id, invoice_number, issue_date, due_date, status,
                subtotal, gst_amount, total, balance_due
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                booking_id,
                client_id,
                invoice_number,
                issue_date.isoformat(),
                (issue_date + dt.timedelta(days=7)).isoformat(),
                "issued",
                round(subtotal, 2),
                gst_amount,
                total,
                round(balance, 2),
            ),
        )
        invoice_id = cur.lastrowid
        for description, price, taxable in pet_prices:
            self.conn.execute(
                """
                INSERT INTO invoice_line_items(
                    invoice_id, description, quantity, unit_price, gst_rate, total
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    description,
                    1,
                    round(price, 2),
                    GST_RATE if taxable else 0,
                    round(price, 2),
                ),
            )
        for row in service_rows:
            description = row["description"]
            line_total = round(row["price"] * row["quantity"], 2)
            self.conn.execute(
                """
                INSERT INTO invoice_line_items(
                    invoice_id, description, quantity, unit_price, gst_rate, total
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    description,
                    row["quantity"],
                    row["price"],
                    GST_RATE if row["gst_applicable"] else 0,
                    line_total,
                ),
            )
        if deposit_amount:
            self.record_payment(
                invoice_id=invoice_id,
                amount=deposit_amount,
                method="deposit",
                payment_date=issue_date.isoformat(),
                reference="booking-deposit",
            )
        self.conn.commit()
        return self.get_invoice(invoice_id)

    def _generate_invoice_number(self, issue_date: dt.date) -> str:
        sequence = self._get_next_sequence(f"invoice_{issue_date.year}")
        return f"INV-{issue_date.year}-{sequence:05d}"

    def create_booking(
        self,
        *,
        location_id: int,
        client_id: int,
        start_time: str,
        end_time: str,
        pet_ids: Sequence[int],
        created_by: int | None = None,
        notes: str | None = None,
        services: Sequence[dict] | None = None,
        recurrence_rule: str | None = None,
        deposit_amount: float = 0.0,
        use_package_credit: bool = False,
    ) -> dict:
        location = self.get_location(location_id)
        start_dt = dt.datetime.fromisoformat(start_time)
        end_dt = dt.datetime.fromisoformat(end_time)
        if end_dt <= start_dt:
            raise ValidationError("End time must be after start time")

        for pet_id in pet_ids:
            self._check_vaccination_valid(pet_id, start_dt)

        booked = self._count_pets_booked(
            location_id=location_id, start_time=start_dt, end_time=end_dt
        )
        capacity = location["capacity"]
        if booked + len(pet_ids) > capacity:
            waitlist_ids = []
            for pet_id in pet_ids:
                cur = self.conn.execute(
                    """
                    INSERT INTO waitlist(location_id, client_id, pet_id, requested_start, requested_end)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        location_id,
                        client_id,
                        pet_id,
                        start_time,
                        end_time,
                    ),
                )
                waitlist_ids.append(cur.lastrowid)
            self.conn.commit()
            return {"status": "waitlisted", "waitlist_ids": waitlist_ids}

        cur = self.conn.execute(
            """
            INSERT INTO bookings(location_id, client_id, start_time, end_time, created_by, notes, recurrence_rule)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (location_id, client_id, start_time, end_time, created_by, notes, recurrence_rule),
        )
        booking_id = cur.lastrowid

        pet_prices: list[tuple[str, float, bool]] = []
        discount_multiplier = 1 - (location["second_pet_discount"] or 0) / 100
        for idx, pet_id in enumerate(pet_ids):
            base_price = location["base_daycare_rate"]
            if idx >= 1:
                base_price = round(base_price * discount_multiplier, 2)
            package_id = None
            if use_package_credit:
                package_id = self._redeem_package_credit(client_id)
                base_price = 0
            self.conn.execute(
                """
                INSERT INTO booking_pets(booking_id, pet_id, package_id, price, gst_applicable)
                VALUES (?, ?, ?, ?, ?)
                """,
                (booking_id, pet_id, package_id, base_price, int(base_price > 0)),
            )
            pet = self.get_pet(pet_id)
            pet_prices.append((f"Daycare - {pet['name']}", base_price, base_price > 0))

        service_rows: list[dict] = []
        if services:
            for svc in services:
                service = self.get_service(svc["service_id"])
                quantity = svc.get("quantity", 1)
                self.conn.execute(
                    """
                    INSERT INTO booking_services(booking_id, service_id, quantity, price, gst_applicable)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        booking_id,
                        service["id"],
                        quantity,
                        service["price"],
                        service["gst_applicable"],
                    ),
                )
                service_rows.append(
                    {
                        "description": service["name"],
                        "price": service["price"],
                        "quantity": quantity,
                        "gst_applicable": bool(service["gst_applicable"]),
                    }
                )

        invoice = self._create_invoice_for_booking(
            booking_id=booking_id,
            client_id=client_id,
            pet_prices=pet_prices,
            service_rows=service_rows,
            issue_date=start_dt.date(),
            deposit_amount=deposit_amount,
        )

        if recurrence_rule:
            self.create_recurring_booking(
                location_id=location_id,
                client_id=client_id,
                start_date=start_dt.date().isoformat(),
                end_date=None,
                start_time=start_dt.time().isoformat(timespec="minutes"),
                end_time=end_dt.time().isoformat(timespec="minutes"),
                rule=recurrence_rule,
            )

        self.conn.commit()
        booking = self.get_booking(booking_id)
        booking["invoice"] = invoice
        return booking

    def _redeem_package_credit(self, client_id: int) -> int:
        row = self.conn.execute(
            """
            SELECT id, remaining_credits FROM client_packages
            WHERE client_id = ? AND (expiry_date IS NULL OR expiry_date >= ?)
            ORDER BY expiry_date ASC NULLS LAST, purchase_date ASC
            LIMIT 1
            """,
            (client_id, dt.date.today().isoformat()),
        ).fetchone()
        if not row:
            raise ValidationError("Client has no available package credits")
        if row["remaining_credits"] <= 0:
            raise ValidationError("Selected package has no remaining credits")
        self.conn.execute(
            "UPDATE client_packages SET remaining_credits = remaining_credits - 1 WHERE id = ?",
            (row["id"],),
        )
        return row["id"]

    def get_booking(self, booking_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not row:
            raise ValidationError("Booking not found")
 codex/create-dog-daycare-management-system-yeinmr
        client = self.get_client(row["client_id"])
        pets = self.conn.execute(
            """
            SELECT booking_pets.*, pets.name AS pet_name
            FROM booking_pets
            JOIN pets ON pets.id = booking_pets.pet_id
            WHERE booking_pets.booking_id = ?
            ORDER BY pets.name
            """,
            (booking_id,),
        ).fetchall()
        services = self.conn.execute(
            """
            SELECT booking_services.*, services.name AS service_name
            FROM booking_services
            JOIN services ON services.id = booking_services.service_id
            WHERE booking_services.booking_id = ?
            ORDER BY services.name
            """,
            (booking_id,),
        ).fetchall()
        invoice = self.conn.execute(
            "SELECT * FROM invoices WHERE booking_id = ?", (booking_id,)
        ).fetchone()
        checkins = self.conn.execute(
            """
            SELECT checkins.*, booking_pets.pet_id AS pet_id, pets.name AS pet_name
            FROM checkins
            JOIN booking_pets ON booking_pets.id = checkins.booking_pet_id
            JOIN pets ON pets.id = booking_pets.pet_id
            WHERE booking_pets.booking_id = ?
            ORDER BY checkins.check_in_time
            """,
            (booking_id,),
        ).fetchall()
        row["pets"] = pets
        row["services"] = services
        row["client"] = client
        row["invoice"] = invoice
        row["checkins"] = checkins

        pets = self.conn.execute(
            "SELECT * FROM booking_pets WHERE booking_id = ?", (booking_id,)
        ).fetchall()
        services = self.conn.execute(
            "SELECT * FROM booking_services WHERE booking_id = ?", (booking_id,)
        ).fetchall()
        row["pets"] = pets
        row["services"] = services
 main
        return row

    def list_bookings(self, *, location_id: int, date: str) -> list[dict]:
        start = dt.datetime.fromisoformat(date)
        end = start + dt.timedelta(days=1)
        rows = self.conn.execute(
            """
            SELECT * FROM bookings
            WHERE location_id = ?
              AND start_time >= ? AND start_time < ?
            ORDER BY start_time
            """,
            (location_id, start.isoformat(), end.isoformat()),
        ).fetchall()
        return [self.get_booking(row["id"]) for row in rows]

 codex/create-dog-daycare-management-system-yeinmr
    def location_dashboard(self, *, location_id: int, date: str | None = None) -> dict:
        """Return a snapshot summary for the dashboard view."""

        location = self.get_location(location_id)
        target_date = dt.date.fromisoformat(date) if date else dt.date.today()
        bookings_today = self.list_bookings(
            location_id=location_id, date=target_date.isoformat()
        )
        waitlist_rows = self.list_waitlist(
            location_id=location_id, date=target_date.isoformat()
        )
        occupancy = sum(len(booking["pets"]) for booking in bookings_today)
        waitlist: list[dict] = []
        for entry in waitlist_rows:
            client = self.get_client(entry["client_id"])
            pet = self.get_pet(entry["pet_id"])
            entry = dict(entry)
            entry["client_name"] = f"{client['first_name']} {client['last_name']}"
            entry["pet_name"] = pet["name"]
            waitlist.append(entry)
        outstanding = self.conn.execute(
            """
            SELECT COALESCE(SUM(invoices.balance_due), 0) AS total
            FROM invoices
            LEFT JOIN bookings ON bookings.id = invoices.booking_id
            WHERE invoices.status != 'paid'
              AND (bookings.location_id = ? OR bookings.location_id IS NULL)
            """,
            (location_id,),
        ).fetchone()["total"]
        new_clients = self.conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM clients
            WHERE DATE(created_at) = ?
            """,
            (target_date.isoformat(),),
        ).fetchone()["count"]
        recent_messages = self.conn.execute(
            """
            SELECT messages.*, clients.first_name || ' ' || clients.last_name AS client_name
            FROM messages
            JOIN clients ON clients.id = messages.client_id
            WHERE messages.created_at >= ?
            ORDER BY messages.created_at DESC
            LIMIT 5
            """,
            ((target_date - dt.timedelta(days=7)).isoformat(),),
        ).fetchall()
        return {
            "location": location,
            "date": target_date.isoformat(),
            "bookings": bookings_today,
            "waitlist": waitlist,
            "occupancy": occupancy,
            "capacity": location["capacity"],
            "available": max(location["capacity"] - occupancy, 0),
            "outstanding_balance": round(outstanding or 0, 2),
            "new_clients_today": new_clients,
            "recent_messages": recent_messages,
        }

    def list_bookings_for_client(
        self,
        *,
        client_id: int,
        upcoming_only: bool = True,
        limit: int | None = None,
    ) -> list[dict]:
        """Return bookings for a specific client."""

        self.get_client(client_id)
        params: list[Any] = [client_id]
        where = "WHERE client_id = ?"
        if upcoming_only:
            where += " AND end_time >= ?"
            params.append(dt.datetime.now().isoformat())
        order = " ORDER BY start_time"
        if limit is not None:
            order += " LIMIT ?"
            params.append(limit)
        rows = self.conn.execute(
            f"SELECT * FROM bookings {where}{order}",
            params,
        ).fetchall()
        return [self.get_booking(row["id"]) for row in rows]


 main
    def check_in_pet(
        self,
        *,
        booking_id: int,
        pet_id: int,
        staff_user_id: int | None,
        check_in_time: str,
        waiver_signed: bool = False,
        health_check_passed: bool = True,
        notes: str | None = None,
    ) -> dict:
        booking_pet = self.conn.execute(
            """
            SELECT booking_pets.* FROM booking_pets
            JOIN bookings ON bookings.id = booking_pets.booking_id
            WHERE bookings.id = ? AND booking_pets.pet_id = ?
            """,
            (booking_id, pet_id),
        ).fetchone()
        if not booking_pet:
            raise ValidationError("Pet is not part of this booking")
        existing = self.conn.execute(
            "SELECT id FROM checkins WHERE booking_pet_id = ?", (booking_pet["id"],)
        ).fetchone()
        if existing:
            self.conn.execute(
                """
                UPDATE checkins
                SET check_in_time = ?, staff_user_id = ?, waiver_signed = ?,
                    health_check_passed = ?, notes = ?
                WHERE booking_pet_id = ?
                """,
                (
                    check_in_time,
                    staff_user_id,
                    int(waiver_signed),
                    int(health_check_passed),
                    notes,
                    booking_pet["id"],
                ),
            )
        else:
            self.conn.execute(
                """
                INSERT INTO checkins(
                    booking_pet_id, check_in_time, staff_user_id, waiver_signed, health_check_passed, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    booking_pet["id"],
                    check_in_time,
                    staff_user_id,
                    int(waiver_signed),
                    int(health_check_passed),
                    notes,
                ),
            )
        self.conn.execute(
            "UPDATE bookings SET status = 'checked_in', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (booking_id,),
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT * FROM checkins WHERE booking_pet_id = ?", (booking_pet["id"],)
        ).fetchone()

    def check_out_pet(
        self,
        *,
        booking_id: int,
        pet_id: int,
        check_out_time: str,
    ) -> dict:
        booking_pet = self.conn.execute(
            "SELECT * FROM booking_pets WHERE booking_id = ? AND pet_id = ?",
            (booking_id, pet_id),
        ).fetchone()
        if not booking_pet:
            raise ValidationError("Pet is not part of this booking")
        row = self.conn.execute(
            "SELECT * FROM checkins WHERE booking_pet_id = ?", (booking_pet["id"],)
        ).fetchone()
        if not row:
            raise ValidationError("Pet has not been checked in")
        self.conn.execute(
            "UPDATE checkins SET check_out_time = ? WHERE booking_pet_id = ?",
            (check_out_time, booking_pet["id"]),
        )
        remaining = self.conn.execute(
            "SELECT COUNT(*) AS remaining FROM checkins WHERE booking_pet_id IN (SELECT id FROM booking_pets WHERE booking_id = ?) AND check_out_time IS NULL",
            (booking_id,),
        ).fetchone()
        if remaining["remaining"] == 0:
            self.conn.execute(
                "UPDATE bookings SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (booking_id,),
            )
        self.conn.commit()
        return self.conn.execute(
            "SELECT * FROM checkins WHERE booking_pet_id = ?", (booking_pet["id"],)
        ).fetchone()

    def log_activity(
        self,
        *,
        pet_id: int,
        activity_type: str,
        details: str,
        booking_id: int | None = None,
        logged_by: int | None = None,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO pet_activity_logs(pet_id, booking_id, activity_type, details, logged_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (pet_id, booking_id, activity_type, details, logged_by),
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT * FROM pet_activity_logs WHERE id = ?", (cur.lastrowid,)
        ).fetchone()

 codex/create-dog-daycare-management-system-yeinmr
    def list_activity_logs(self, *, pet_id: int) -> list[dict]:
        """Return activity entries for a pet."""

        self.get_pet(pet_id)
        return self.conn.execute(
            """
            SELECT pet_activity_logs.*, users.name AS staff_name
            FROM pet_activity_logs
            LEFT JOIN users ON users.id = pet_activity_logs.logged_by
            WHERE pet_activity_logs.pet_id = ?
            ORDER BY pet_activity_logs.created_at DESC
            """,
            (pet_id,),
        ).fetchall()


 main
    # ------------------------------------------------------------------
    # Billing
    # ------------------------------------------------------------------
    def get_invoice(self, invoice_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not row:
            raise ValidationError("Invoice not found")
        lines = self.conn.execute(
            "SELECT * FROM invoice_line_items WHERE invoice_id = ?",
            (invoice_id,),
        ).fetchall()
        payments = self.conn.execute(
            "SELECT * FROM payments WHERE invoice_id = ?",
            (invoice_id,),
        ).fetchall()
        row["line_items"] = lines
        row["payments"] = payments
        return row

 codex/create-dog-daycare-management-system-yeinmr
    def list_invoices(
        self,
        *,
        client_id: int | None = None,
        status: Sequence[str] | None = None,
    ) -> list[dict]:
        """Return invoices optionally filtered by client or status."""

        params: list[Any] = []
        conditions: list[str] = []
        if client_id is not None:
            conditions.append("invoices.client_id = ?")
            params.append(client_id)
        if status:
            placeholders = ",".join("?" for _ in status)
            conditions.append(f"invoices.status IN ({placeholders})")
            params.extend(status)
        where = ""
        if conditions:
            where = " WHERE " + " AND ".join(conditions)
        query = (
            """
            SELECT invoices.*, bookings.start_time, bookings.location_id
            FROM invoices
            LEFT JOIN bookings ON bookings.id = invoices.booking_id
            {where}
            ORDER BY issue_date DESC, invoices.id DESC
            """.format(where=where)
        )
        return self.conn.execute(query, params).fetchall()


 main
    def record_payment(
        self,
        *,
        invoice_id: int,
        amount: float,
        method: str,
        payment_date: str,
        reference: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        invoice = self.conn.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
        if not invoice:
            raise ValidationError("Invoice not found")
        self.conn.execute(
            """
            INSERT INTO payments(invoice_id, amount, method, payment_date, reference, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (invoice_id, amount, method, payment_date, reference, json.dumps(metadata or {})),
        )
        new_balance = round(invoice["balance_due"] - amount, 2)
        status = "paid" if new_balance <= 0 else invoice["status"]
        self.conn.execute(
            "UPDATE invoices SET balance_due = ?, status = ? WHERE id = ?",
            (new_balance, status, invoice_id),
        )
        self.conn.commit()
        return self.get_invoice(invoice_id)

    # ------------------------------------------------------------------
    # Communications & documents
    # ------------------------------------------------------------------
    def send_notification(
        self,
        *,
        client_id: int,
        channel: str,
        template_code: str,
        content: str,
        metadata: dict | None = None,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO notifications(client_id, channel, template_code, content, metadata, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (client_id, channel, template_code, content, json.dumps(metadata or {}), "sent"),
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT * FROM notifications WHERE id = ?", (cur.lastrowid,)
        ).fetchone()

 codex/create-dog-daycare-management-system-yeinmr
    def list_notifications(self, *, client_id: int) -> list[dict]:
        """Return notifications previously sent to a client."""

        self.get_client(client_id)
        return self.conn.execute(
            """
            SELECT * FROM notifications
            WHERE client_id = ?
            ORDER BY created_at DESC
            """,
            (client_id,),
        ).fetchall()


 main
    def log_message(
        self,
        *,
        client_id: int,
        direction: str,
        channel: str,
        content: str,
        staff_user_id: int | None = None,
        related_booking_id: int | None = None,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO messages(client_id, direction, channel, content, staff_user_id, related_booking_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (client_id, direction, channel, content, staff_user_id, related_booking_id),
        )
        self.conn.commit()
 codex/create-dog-daycare-management-system-yeinmr
        return self.conn.execute(
            "SELECT * FROM messages WHERE id = ?", (cur.lastrowid,)
        ).fetchone()

    def list_messages(self, *, client_id: int) -> list[dict]:
        """Return the two-way communication history for a client."""

        self.get_client(client_id)
        return self.conn.execute(
            """
            SELECT messages.*, users.name AS staff_name
            FROM messages
            LEFT JOIN users ON users.id = messages.staff_user_id
            WHERE messages.client_id = ?
            ORDER BY messages.created_at DESC
            """,
            (client_id,),
        ).fetchall()

        return self.conn.execute("SELECT * FROM messages WHERE id = ?", (cur.lastrowid,)).fetchone()
 main

    def create_document(
        self,
        *,
        name: str,
        description: str,
        content: str,
        requires_signature: bool = True,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO documents(name, description, content, requires_signature)
            VALUES (?, ?, ?, ?)
            """,
            (name, description, content, int(requires_signature)),
        )
        self.conn.commit()
        return self.conn.execute("SELECT * FROM documents WHERE id = ?", (cur.lastrowid,)).fetchone()

    def assign_document(
        self,
        *,
        document_id: int,
        client_id: int,
        due_date: str | None = None,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO document_assignments(document_id, client_id, due_date)
            VALUES (?, ?, ?)
            """,
            (document_id, client_id, due_date),
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT * FROM document_assignments WHERE id = ?", (cur.lastrowid,)
        ).fetchone()

    def complete_document(
        self,
        *,
        assignment_id: int,
        signed_at: str,
        captured_data: dict | None = None,
    ) -> dict:
        self.conn.execute(
            """
            UPDATE document_assignments
            SET status = 'completed', signed_at = ?, captured_data = ?
            WHERE id = ?
            """,
            (signed_at, json.dumps(captured_data or {}), assignment_id),
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT * FROM document_assignments WHERE id = ?", (assignment_id,)
        ).fetchone()

    # ------------------------------------------------------------------
    # Staff management
    # ------------------------------------------------------------------
    def create_employee(
        self,
        *,
        user_id: int,
        position: str,
        hourly_rate: float,
        started_on: str,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO employees(user_id, position, hourly_rate, started_on)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, position, hourly_rate, started_on),
        )
        self.conn.commit()
        return self.conn.execute("SELECT * FROM employees WHERE id = ?", (cur.lastrowid,)).fetchone()

    def schedule_shift(
        self,
        *,
        employee_id: int,
        location_id: int,
        start_time: str,
        end_time: str,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO staff_shifts(employee_id, location_id, start_time, end_time)
            VALUES (?, ?, ?, ?)
            """,
            (employee_id, location_id, start_time, end_time),
        )
        self.conn.commit()
        return self.conn.execute("SELECT * FROM staff_shifts WHERE id = ?", (cur.lastrowid,)).fetchone()

    def clock_in(self, *, employee_id: int, clock_in: str) -> dict:
        cur = self.conn.execute(
            "INSERT INTO time_clock_entries(employee_id, clock_in) VALUES (?, ?)",
            (employee_id, clock_in),
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT * FROM time_clock_entries WHERE id = ?", (cur.lastrowid,)
        ).fetchone()

    def clock_out(self, *, entry_id: int, clock_out: str) -> dict:
        self.conn.execute(
            "UPDATE time_clock_entries SET clock_out = ? WHERE id = ?", (clock_out, entry_id)
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT * FROM time_clock_entries WHERE id = ?", (entry_id,)
        ).fetchone()

    # ------------------------------------------------------------------
    # Waitlist and recurring bookings
    # ------------------------------------------------------------------
    def list_waitlist(self, *, location_id: int, date: str) -> list[dict]:
        start = dt.datetime.fromisoformat(date)
        end = start + dt.timedelta(days=1)
        rows = self.conn.execute(
            """
            SELECT * FROM waitlist
            WHERE location_id = ? AND requested_start >= ? AND requested_start < ?
            ORDER BY created_at
            """,
            (location_id, start.isoformat(), end.isoformat()),
        ).fetchall()
        return rows

    def promote_waitlist(self, waitlist_id: int) -> dict:
        entry = self.conn.execute(
            "SELECT * FROM waitlist WHERE id = ?", (waitlist_id,)
        ).fetchone()
        if not entry:
            raise ValidationError("Waitlist entry not found")
        booking = self.create_booking(
            location_id=entry["location_id"],
            client_id=entry["client_id"],
            start_time=entry["requested_start"],
            end_time=entry["requested_end"],
            pet_ids=[entry["pet_id"]],
            use_package_credit=False,
        )
        self.conn.execute(
            "UPDATE waitlist SET status = 'converted' WHERE id = ?", (waitlist_id,)
        )
        self.conn.commit()
        return booking

    def create_recurring_booking(
        self,
        *,
        location_id: int,
        client_id: int,
        rule: str,
        start_date: str,
        start_time: str,
        end_time: str,
        end_date: str | None,
        metadata: dict | None = None,
    ) -> dict:
        cur = self.conn.execute(
            """
            INSERT INTO recurring_bookings(location_id, client_id, rule, start_date, end_date, start_time, end_time, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                location_id,
                client_id,
                rule,
                start_date,
                end_date,
                start_time,
                end_time,
                json.dumps(metadata or {}),
            ),
        )
        self.conn.commit()
        return self.conn.execute(
            "SELECT * FROM recurring_bookings WHERE id = ?", (cur.lastrowid,)
        ).fetchone()

    # ------------------------------------------------------------------
    # Reporting & integrations
    # ------------------------------------------------------------------
    def occupancy_report(
        self,
        *,
        location_id: int,
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        start = dt.datetime.fromisoformat(start_date)
        end = dt.datetime.fromisoformat(end_date) + dt.timedelta(days=1)
        rows = self.conn.execute(
            """
            SELECT date(start_time) as service_date, COUNT(booking_pets.id) AS pets
            FROM bookings
            JOIN booking_pets ON booking_pets.booking_id = bookings.id
            WHERE bookings.location_id = ?
              AND bookings.start_time >= ? AND bookings.start_time <= ?
            GROUP BY date(start_time)
            ORDER BY service_date
            """,
            (location_id, start.isoformat(), end.isoformat()),
        ).fetchall()
        return rows

    def revenue_report(
        self,
        *,
        start_date: str,
        end_date: str,
        location_id: int | None = None,
    ) -> dict:
        params: list[Any] = [start_date, end_date]
        where = "issue_date >= ? AND issue_date <= ?"
        if location_id:
            where += " AND booking_id IN (SELECT id FROM bookings WHERE location_id = ?)"
            params.append(location_id)
        rows = self.conn.execute(
            f"SELECT SUM(total) AS total_revenue, SUM(gst_amount) AS gst_collected FROM invoices WHERE {where}",
            params,
        ).fetchone()
        payments = self.conn.execute(
            """
            SELECT method, SUM(amount) AS total FROM payments
            WHERE payment_date >= ? AND payment_date <= ?
            GROUP BY method
            """,
            (start_date, end_date),
        ).fetchall()
        return {
            "revenue": rows["total_revenue"] or 0,
            "gst_collected": rows["gst_collected"] or 0,
            "payments": payments,
        }

    def outstanding_balances(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM invoices WHERE balance_due > 0 ORDER BY issue_date"
        ).fetchall()
        return rows

    def package_usage_report(self, *, client_id: int) -> dict:
        rows = self.conn.execute(
            "SELECT * FROM client_packages WHERE client_id = ?",
            (client_id,),
        ).fetchall()
        total_purchased = sum(row["remaining_credits"] for row in rows)
        return {"packages": rows, "total_available": total_purchased}

    def export_for_xero(self, *, invoice_id: int) -> dict:
        invoice = self.get_invoice(invoice_id)
        contact = self.get_client(invoice["client_id"])
        return {
            "Type": "ACCREC",
            "Contact": {
                "Name": f"{contact['first_name']} {contact['last_name']}",
                "EmailAddress": contact["email"],
            },
            "Date": invoice["issue_date"],
            "DueDate": invoice["due_date"],
            "LineAmountTypes": "Inclusive",
            "LineItems": [
                {
                    "Description": item["description"],
                    "Quantity": item["quantity"],
                    "UnitAmount": item["unit_price"],
                    "TaxAmount": round(item["total"] * GST_RATE, 2),
                }
                for item in invoice["line_items"]
            ],
            "AmountDue": invoice["balance_due"],
        }

    def calendar_view(
        self,
        *,
        location_id: int,
        target_date: str,
    ) -> dict:
        bookings = self.list_bookings(location_id=location_id, date=target_date)
        schedule = defaultdict(list)
        for booking in bookings:
            day = booking["start_time"][:10]
            schedule[day].append(booking)
        return {"date": target_date, "bookings": schedule}

    def close(self) -> None:
        self.conn.close()
