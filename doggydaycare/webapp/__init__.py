"""Flask application providing a simple UI for the daycare system."""

from __future__ import annotations

import datetime as dt
from typing import Any

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from doggydaycare.daycare.system import DaycareSystem, ValidationError


def create_app(database_path: str = "daycare_app.db") -> Flask:
    """Create and configure the Flask application."""

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = "daycare-secret"

    system = DaycareSystem(database_path)

    @app.before_request
    def ensure_location_selected() -> None:
        locations = system.list_locations()
        if locations and "location_id" not in session:
            session["location_id"] = locations[0]["id"]

    @app.context_processor
    def inject_navigation() -> dict[str, Any]:
        locations = system.list_locations()
        active_id = session.get("location_id")
        active_location = None
        for location in locations:
            if location["id"] == active_id:
                active_location = location
                break
        return {
            "locations": locations,
            "active_location": active_location,
            "current_year": dt.date.today().year,
        }

    @app.get("/")
    def index() -> Any:
        return redirect(url_for("dashboard"))

    @app.post("/select-location")
    def select_location() -> Any:
        location_id = request.form.get("location_id", type=int)
        if location_id:
            session["location_id"] = location_id
        return redirect(request.referrer or url_for("dashboard"))

    @app.route("/dashboard")
    def dashboard() -> Any:
        locations = system.list_locations()
        if not locations:
            return render_template("setup.html")
        location_id = session.get("location_id") or locations[0]["id"]
        if not any(loc["id"] == location_id for loc in locations):
            location_id = locations[0]["id"]
            session["location_id"] = location_id
        snapshot = system.location_dashboard(location_id=location_id)
        invoices_all = system.list_invoices(status=("sent", "partial", "overdue"))
        open_invoices = [
            invoice for invoice in invoices_all if invoice["location_id"] in (None, location_id)
        ]
        clients_all = system.list_clients()
        recent_clients = clients_all[:5]
        clients_by_id = {client["id"]: client for client in clients_all}
        staff = system.list_users(location_id=location_id)
        return render_template(
            "dashboard.html",
            snapshot=snapshot,
            open_invoices=open_invoices,
            recent_clients=recent_clients,
            clients_by_id=clients_by_id,
            staff=staff,
        )

    @app.route("/locations", methods=["GET", "POST"])
    def locations() -> Any:
        if request.method == "POST":
            try:
                system.create_location(
                    name=request.form.get("name", "").strip(),
                    capacity=request.form.get("capacity", type=int) or 0,
                    base_daycare_rate=request.form.get("base_daycare_rate", type=float) or 0.0,
                    second_pet_discount=request.form.get("second_pet_discount", type=float) or 0.0,
                    timezone=request.form.get("timezone", "Australia/Sydney"),
                    address=request.form.get("address") or None,
                    suburb=request.form.get("suburb") or None,
                    state=request.form.get("state") or None,
                    postcode=request.form.get("postcode") or None,
                    gst_registered=request.form.get("gst_registered") is not None,
                )
                flash("Location created", "success")
                return redirect(url_for("locations"))
            except ValidationError as exc:
                flash(str(exc), "error")
        return render_template("locations.html", locations=system.list_locations())

    @app.route("/clients", methods=["GET", "POST"])
    def clients() -> Any:
        if request.method == "POST":
            try:
                system.register_client(
                    first_name=request.form["first_name"].strip(),
                    last_name=request.form["last_name"].strip(),
                    phone=request.form.get("phone", "").strip(),
                    email=request.form.get("email", "").strip(),
                    address=request.form.get("address") or None,
                    suburb=request.form.get("suburb") or None,
                    state=request.form.get("state") or None,
                    postcode=request.form.get("postcode") or None,
                    emergency_contact_name=request.form.get("emergency_contact_name") or None,
                    emergency_contact_phone=request.form.get("emergency_contact_phone") or None,
                    marketing_opt_in=bool(request.form.get("marketing_opt_in")),
                    notes=request.form.get("notes") or None,
                )
                flash("Client added", "success")
                return redirect(url_for("clients"))
            except ValidationError as exc:
                flash(str(exc), "error")
        return render_template("clients.html", clients=system.list_clients())

    @app.get("/clients/<int:client_id>")
    def client_detail(client_id: int) -> Any:
        client = system.get_client(client_id)
        pets = system.list_pets(client_id=client_id)
        for pet in pets:
            pet["vaccinations"] = system.list_vaccinations(pet_id=pet["id"])
            pet["notes"] = system.list_pet_notes(pet_id=pet["id"])
            pet["activities"] = system.list_activity_logs(pet_id=pet["id"])
        location_id = session.get("location_id")
        upcoming = system.list_bookings_for_client(client_id=client_id, upcoming_only=True)
        history = system.list_bookings_for_client(
            client_id=client_id, upcoming_only=False, limit=20
        )
        invoices = system.list_invoices(client_id=client_id)
        packages = system.list_client_packages(client_id=client_id)
        available_packages = system.list_packages(location_id=location_id)
        services = system.list_services(location_id=location_id)
        notifications = system.list_notifications(client_id=client_id)
        messages = system.list_messages(client_id=client_id)
        return render_template(
            "client_detail.html",
            client=client,
            pets=pets,
            upcoming_bookings=upcoming,
            booking_history=history,
            invoices=invoices,
            packages=packages,
            available_packages=available_packages,
            services=services,
            notifications=notifications,
            messages=messages,
        )

    @app.post("/clients/<int:client_id>/pets")
    def add_pet(client_id: int) -> Any:
        try:
            system.add_pet(
                client_id=client_id,
                name=request.form["name"].strip(),
                breed=request.form.get("breed") or None,
                birth_date=request.form.get("birth_date") or None,
                gender=request.form.get("gender") or None,
                colour=request.form.get("colour") or None,
                medical_notes=request.form.get("medical_notes") or None,
                feeding_instructions=request.form.get("feeding_instructions") or None,
                behaviour_flags=request.form.get("behaviour_flags") or None,
                allergies=request.form.get("allergies") or None,
            )
            flash("Pet added", "success")
        except ValidationError as exc:
            flash(str(exc), "error")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.post("/pets/<int:pet_id>/vaccinations")
    def add_vaccination(pet_id: int) -> Any:
        client_id = int(request.form["client_id"])
        try:
            system.record_vaccination(
                pet_id=pet_id,
                vaccine_name=request.form["vaccine_name"].strip(),
                expiry_date=request.form["expiry_date"],
                document_url=request.form.get("document_url") or None,
                notes=request.form.get("notes") or None,
            )
            flash("Vaccination recorded", "success")
        except ValidationError as exc:
            flash(str(exc), "error")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.post("/pets/<int:pet_id>/notes")
    def add_pet_note(pet_id: int) -> Any:
        client_id = int(request.form["client_id"])
        try:
            system.add_pet_note(
                pet_id=pet_id,
                note=request.form["note"],
                flag_type=request.form.get("flag_type") or None,
                severity=request.form.get("severity") or None,
            )
            flash("Note added", "success")
        except ValidationError as exc:
            flash(str(exc), "error")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.post("/clients/<int:client_id>/packages")
    def sell_package(client_id: int) -> Any:
        try:
            system.sell_package(
                client_id=client_id,
                package_id=request.form.get("package_id", type=int),
                purchase_date=dt.date.today().isoformat(),
                expiry_date=request.form.get("expiry_date") or None,
            )
            flash("Package sold", "success")
        except ValidationError as exc:
            flash(str(exc), "error")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.post("/clients/<int:client_id>/bookings")
    def create_client_booking(client_id: int) -> Any:
        location_id = session.get("location_id")
        if not location_id:
            flash("Create a location before booking", "error")
            return redirect(url_for("client_detail", client_id=client_id))
        pet_ids = [int(pid) for pid in request.form.getlist("pet_ids") if pid]
        services = []
        service_id = request.form.get("service_id", type=int)
        if service_id:
            services.append(
                {
                    "service_id": service_id,
                    "quantity": request.form.get("service_quantity", type=int) or 1,
                }
            )
        try:
            booking = system.create_booking(
                location_id=location_id,
                client_id=client_id,
                start_time=request.form["start_time"],
                end_time=request.form["end_time"],
                pet_ids=pet_ids,
                notes=request.form.get("notes") or None,
                services=services or None,
                use_package_credit=bool(request.form.get("use_package_credit")),
            )
            if booking.get("status") == "waitlisted":
                flash("Booking added to waitlist due to capacity", "warning")
            else:
                flash("Booking created", "success")
        except ValidationError as exc:
            flash(str(exc), "error")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.post("/clients/<int:client_id>/messages")
    def send_message(client_id: int) -> Any:
        try:
            system.log_message(
                client_id=client_id,
                direction="outbound",
                channel=request.form.get("channel", "email"),
                content=request.form["content"],
            )
            flash("Message logged", "success")
        except ValidationError as exc:
            flash(str(exc), "error")
        return redirect(url_for("client_detail", client_id=client_id))

    @app.route("/bookings")
    def bookings() -> Any:
        locations = system.list_locations()
        if not locations:
            return render_template("bookings.html", bookings=[], waitlist=[], date=None)
        location_id = session.get("location_id") or locations[0]["id"]
        date = request.args.get("date") or dt.date.today().isoformat()
        bookings = system.list_bookings(location_id=location_id, date=date)
        waitlist = system.list_waitlist(location_id=location_id, date=date)
        pets_lookup = {pet["id"]: pet for pet in system.list_pets(include_archived=True)}
        for entry in waitlist:
            pet = pets_lookup.get(entry["pet_id"])
            if pet:
                entry["pet_name"] = pet["name"]
                entry["client_name"] = pet["owner_name"]
        services = system.list_services(location_id=location_id)
        clients = system.list_clients()
        return render_template(
            "bookings.html",
            bookings=bookings,
            waitlist=waitlist,
            services=services,
            clients=clients,
            pets=system.list_pets(),
            date=date,
        )

    @app.post("/bookings")
    def create_booking_route() -> Any:
        location_id = session.get("location_id")
        if not location_id:
            flash("Set up a location first", "error")
            return redirect(url_for("bookings"))
        client_id = request.form.get("client_id", type=int)
        pet_ids = [int(pid) for pid in request.form.getlist("pet_ids") if pid]
        services = []
        service_id = request.form.get("service_id", type=int)
        if service_id:
            services.append(
                {
                    "service_id": service_id,
                    "quantity": request.form.get("service_quantity", type=int) or 1,
                }
            )
        try:
            booking = system.create_booking(
                location_id=location_id,
                client_id=client_id,
                start_time=request.form["start_time"],
                end_time=request.form["end_time"],
                pet_ids=pet_ids,
                notes=request.form.get("notes") or None,
                services=services or None,
                use_package_credit=bool(request.form.get("use_package_credit")),
            )
            if booking.get("status") == "waitlisted":
                flash("Booking added to waitlist", "warning")
            else:
                flash("Booking created", "success")
        except ValidationError as exc:
            flash(str(exc), "error")
        return redirect(url_for("bookings", date=request.form["start_time"][0:10]))

    @app.post("/bookings/<int:booking_id>/checkin")
    def checkin(booking_id: int) -> Any:
        pet_id = request.form.get("pet_id", type=int)
        try:
            system.check_in_pet(
                booking_id=booking_id,
                pet_id=pet_id,
                staff_user_id=request.form.get("staff_user_id", type=int),
                check_in_time=dt.datetime.now().isoformat(timespec="minutes"),
                waiver_signed=bool(request.form.get("waiver_signed")),
                health_check_passed=not request.form.get("health_issue"),
                notes=request.form.get("notes") or None,
            )
            flash("Pet checked in", "success")
        except ValidationError as exc:
            flash(str(exc), "error")
        return redirect(request.referrer or url_for("bookings"))

    @app.post("/bookings/<int:booking_id>/checkout")
    def checkout(booking_id: int) -> Any:
        pet_id = request.form.get("pet_id", type=int)
        try:
            system.check_out_pet(
                booking_id=booking_id,
                pet_id=pet_id,
                check_out_time=dt.datetime.now().isoformat(timespec="minutes"),
            )
            flash("Pet checked out", "success")
        except ValidationError as exc:
            flash(str(exc), "error")
        return redirect(request.referrer or url_for("bookings"))

    @app.route("/invoices")
    def invoices() -> Any:
        location_id = session.get("location_id")
        invoices = system.list_invoices()
        clients = {client["id"]: client for client in system.list_clients()}
        return render_template(
            "invoices.html",
            invoices=invoices,
            clients=clients,
            location_id=location_id,
        )

    @app.post("/invoices/<int:invoice_id>/payments")
    def record_payment(invoice_id: int) -> Any:
        try:
            system.record_payment(
                invoice_id=invoice_id,
                amount=request.form.get("amount", type=float) or 0.0,
                method=request.form.get("method", "cash"),
                payment_date=dt.date.today().isoformat(),
                reference=request.form.get("reference") or None,
            )
            flash("Payment recorded", "success")
        except ValidationError as exc:
            flash(str(exc), "error")
        return redirect(request.referrer or url_for("invoices"))

    return app


__all__ = ["create_app"]
