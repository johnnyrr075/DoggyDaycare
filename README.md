# Doggy Daycare Management Platform

This project implements a comprehensive management back-end for Australian dog daycare businesses. It was designed from market research covering core operational requirements (bookings, client and pet records, invoicing with GST, packages, communications) and competitive differentiators (multi-location support, staff time tracking, inventory, client engagement, integrations).

The platform is delivered as a Python module backed by SQLite with no third-party dependencies, making it portable and easy to run in constrained environments. The `DaycareSystem` façade in `doggydaycare/daycare/system.py` exposes high-level workflows that cover the lifecycle of a daycare visit, from online booking and waitlisting, to check-in/out, billing, communications, and reporting.

## Key Capabilities

- **Pet & Client CRM** – manage detailed owner and pet profiles, including vaccination records, behavioural flags, and notes.
- **Scheduling & Capacity Control** – create bookings with multiple pets per family, enforce location capacity, support recurring reservations, waitlists, and calendar exports.
- **Check-In/Out & Daily Operations** – capture digital waivers, record attendance, log feeding/medication events, and send same-day updates.
- **Packages & Memberships** – sell and redeem multi-day passes with automatic credit tracking and loyalty-friendly metadata.
- **Billing & GST Compliance** – generate tax invoices with GST calculations, accept deposits, record payments, and export records to Xero-compatible payloads.
- **Customer Engagement** – deliver notifications, maintain two-way message logs, capture digital forms, and produce pet “report card” activity notes.
- **Business Intelligence** – produce occupancy, revenue, outstanding balance, and package usage reports for single or multi-location operators.
- **Staff & Inventory Tools** – manage employee shifts, capture time clock entries, track retail stock movements, and associate sales with invoices.

## Project Structure

```
README.md
 doggydaycare/
 ├── __init__.py
 ├── daycare/
 │   ├── __init__.py
 │   ├── database.py      # SQLite schema and connection helpers
 │   └── system.py        # High-level orchestration class
 └── tests/
     └── test_daycare_system.py  # End-to-end coverage of major workflows
```

## Getting Started

1. Run the automated tests to verify the system functions as expected:

   ```bash
   python -m unittest discover doggydaycare/tests
   ```

2. Import and use the `DaycareSystem` class in your own scripts or services:

   ```python
   from doggydaycare.daycare.system import DaycareSystem

   system = DaycareSystem("doggydaycare.db")
   location = system.create_location(name="Melbourne", capacity=30, base_daycare_rate=60.0)
   client = system.register_client(first_name="Alex", last_name="Lee", phone="0412345678", email="alex@example.com")
   pet = system.add_pet(client_id=client["id"], name="Scout", breed="Cavoodle")
   system.record_vaccination(pet_id=pet["id"], vaccine_name="C5", expiry_date="2026-01-01")
   booking = system.create_booking(
       location_id=location["id"],
       client_id=client["id"],
       start_time="2025-02-10T08:00:00",
       end_time="2025-02-10T17:30:00",
       pet_ids=[pet["id"]],
   )
   print("Invoice total:", booking["invoice"]["total"])
   system.close()
   ```

## Design Notes

- **No external dependencies:** All functionality relies on Python’s standard library to remain deployable without internet access or package managers.
- **Extensible schema:** The SQLite schema models locations, users, pets, bookings, services, packages, invoices, notifications, employees, inventory, and digital documents, enabling future UI layers or mobile apps to build on the same data model.
- **Australian context:** GST is calculated at 10%, invoices capture local address fields (suburb, postcode), and exports target Xero/BAS workflows.
- **Scalability:** Multi-location support, recurring bookings, and structured metadata columns allow the system to grow towards franchise operations or integrate with third-party services.

## Running the Test Suite

A comprehensive integration test validates the primary business flow, including booking, waitlisting, payments, reporting, communications, and staff tooling. Execute the suite with:

```bash
python -m unittest discover doggydaycare/tests
```

This command must succeed before submitting changes.

## Next Steps

To extend the project, consider adding a lightweight HTTP or GraphQL API, progressive web app client, or background workers for message delivery. The existing `DaycareSystem` acts as a service layer ready to be wrapped by whichever interface best suits the business.
