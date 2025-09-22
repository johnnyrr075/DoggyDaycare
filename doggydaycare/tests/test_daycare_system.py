import datetime as dt
import unittest

from doggydaycare.daycare.system import DaycareSystem, ValidationError


class DaycareSystemTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.system = DaycareSystem()
        self.today = dt.date.today()
        self.location = self.system.create_location(
            name="Sydney CBD",
            capacity=2,
            base_daycare_rate=65.0,
            second_pet_discount=20,
            timezone="Australia/Sydney",
            address="1 Market St",
            suburb="Sydney",
            state="NSW",
            postcode="2000",
        )
        self.manager = self.system.register_user(
            email="manager@example.com",
            password="Password!23",
            role="manager",
            name="Casey Manager",
        )
        self.client = self.system.register_client(
            first_name="Jordan",
            last_name="River",
            phone="0400000000",
            email="jordan@example.com",
            address="12 Pet Lane",
            suburb="Sydney",
            state="NSW",
            postcode="2001",
        )
        expiry = (self.today + dt.timedelta(days=180)).isoformat()
        self.pet_a = self.system.add_pet(client_id=self.client["id"], name="Rex", breed="Kelpie")
        self.pet_b = self.system.add_pet(client_id=self.client["id"], name="Molly", breed="Border Collie")
        self.pet_c = self.system.add_pet(client_id=self.client["id"], name="Otis", breed="Beagle")
        for pet in (self.pet_a, self.pet_b, self.pet_c):
            self.system.record_vaccination(pet_id=pet["id"], vaccine_name="C5", expiry_date=expiry)
        self.service = self.system.create_service(
            name="Grooming",
            price=25.0,
            description="Wash & dry",
            default_duration_minutes=45,
            gst_applicable=True,
            location_id=self.location["id"],
        )
        self.package = self.system.create_daycare_package(
            name="10 Day Pass",
            description="Pre-paid pass",
            location_id=self.location["id"],
            total_credits=10,
            price=590.0,
            valid_days=365,
        )
        self.client_package = self.system.sell_package(
            client_id=self.client["id"],
            package_id=self.package["id"],
            purchase_date=self.today.isoformat(),
            expiry_date=(self.today + dt.timedelta(days=365)).isoformat(),
        )
        self.document = self.system.create_document(
            name="Daycare Waiver",
            description="General liability waiver",
            content="I agree to the terms.",
        )

    def tearDown(self) -> None:
        self.system.close()

    def test_end_to_end_booking_flow(self) -> None:
        start = dt.datetime.combine(self.today, dt.time(8, 0)).isoformat()
        end = dt.datetime.combine(self.today, dt.time(17, 0)).isoformat()
        booking = self.system.create_booking(
            location_id=self.location["id"],
            client_id=self.client["id"],
            start_time=start,
            end_time=end,
            pet_ids=[self.pet_a["id"], self.pet_b["id"]],
            created_by=self.manager["id"],
            services=[{"service_id": self.service["id"], "quantity": 1}],
            deposit_amount=5.0,
            use_package_credit=True,
            recurrence_rule="RRULE:FREQ=WEEKLY;COUNT=4",
        )
        self.assertIn("invoice", booking)
        invoice = booking["invoice"]
        self.assertAlmostEqual(invoice["total"], 27.5, places=2)
        # Package credits should be reduced
        package = self.system.get_client_package(self.client_package["id"])
        self.assertEqual(package["remaining_credits"], 8)

        # Check-in and check-out first pet
        check_in = self.system.check_in_pet(
            booking_id=booking["id"],
            pet_id=self.pet_a["id"],
            staff_user_id=self.manager["id"],
            check_in_time=start,
            waiver_signed=True,
            health_check_passed=True,
        )
        self.assertTrue(check_in["waiver_signed"])
        self.system.check_in_pet(
            booking_id=booking["id"],
            pet_id=self.pet_b["id"],
            staff_user_id=self.manager["id"],
            check_in_time=start,
            waiver_signed=False,
            health_check_passed=True,
        )
        # Waitlist due to capacity reached while the booking is still active
        waitlist_response = self.system.create_booking(
            location_id=self.location["id"],
            client_id=self.client["id"],
            start_time=start,
            end_time=end,
            pet_ids=[self.pet_c["id"]],
        )
        self.assertEqual(waitlist_response["status"], "waitlisted")
        waitlist_entries = self.system.list_waitlist(
            location_id=self.location["id"], date=self.today.isoformat()
        )
        self.assertEqual(len(waitlist_entries), 1)

        # Complete the booking and settle the invoice
        self.system.check_out_pet(
            booking_id=booking["id"],
            pet_id=self.pet_a["id"],
            check_out_time=end,
        )
        self.system.check_out_pet(
            booking_id=booking["id"],
            pet_id=self.pet_b["id"],
            check_out_time=end,
        )
        updated_invoice = self.system.record_payment(
            invoice_id=invoice["id"],
            amount=22.5,
            method="card",
            payment_date=self.today.isoformat(),
            reference="PAY123",
        )
        self.assertEqual(updated_invoice["balance_due"], 0)
        self.assertEqual(updated_invoice["status"], "paid")

        # After completing the booking, promote from waitlist
        promoted = self.system.promote_waitlist(waitlist_entries[0]["id"])
        self.assertIn("invoice", promoted)

        # Notifications and messaging
        notification = self.system.send_notification(
            client_id=self.client["id"],
            channel="email",
            template_code="booking_confirmation",
            content="Your booking is confirmed",
        )
        self.assertEqual(notification["status"], "sent")
        message = self.system.log_message(
            client_id=self.client["id"],
            direction="outbound",
            channel="sms",
            content="Rex had a great day!",
            staff_user_id=self.manager["id"],
            related_booking_id=booking["id"],
        )
        self.assertEqual(message["direction"], "outbound")

        # Documents
        assignment = self.system.assign_document(
            document_id=self.document["id"],
            client_id=self.client["id"],
            due_date=self.today.isoformat(),
        )
        completed = self.system.complete_document(
            assignment_id=assignment["id"],
            signed_at=self.today.isoformat(),
            captured_data={"signature": "Jordan"},
        )
        self.assertEqual(completed["status"], "completed")

        # Pet activity logging
        activity = self.system.log_activity(
            pet_id=self.pet_a["id"],
            activity_type="Feeding",
            details="Fed chicken meal",
            booking_id=booking["id"],
            logged_by=self.manager["id"],
        )
        self.assertEqual(activity["activity_type"], "Feeding")

        # Inventory management
        item = self.system.create_inventory_item(
            name="Dog Treats",
            sku="TREATS-001",
            quantity=20,
            unit_cost=5.0,
            unit_price=9.5,
        )
        adjusted_item = self.system.adjust_inventory(
            item_id=item["id"],
            quantity_change=-2,
            reason="Sold",
            staff_user_id=self.manager["id"],
            related_invoice_id=invoice["id"],
        )
        self.assertEqual(adjusted_item["quantity"], 18)

        # Staff and time tracking
        employee = self.system.create_employee(
            user_id=self.manager["id"],
            position="Supervisor",
            hourly_rate=32.5,
            started_on=self.today.isoformat(),
        )
        shift = self.system.schedule_shift(
            employee_id=employee["id"],
            location_id=self.location["id"],
            start_time=start,
            end_time=end,
        )
        clock_entry = self.system.clock_in(employee_id=employee["id"], clock_in=start)
        clocked_out = self.system.clock_out(entry_id=clock_entry["id"], clock_out=end)
        self.assertEqual(shift["employee_id"], employee["id"])
        self.assertIsNotNone(clocked_out["clock_out"])

        # Reporting
        occupancy = self.system.occupancy_report(
            location_id=self.location["id"],
            start_date=self.today.isoformat(),
            end_date=self.today.isoformat(),
        )
        self.assertTrue(occupancy)
        revenue = self.system.revenue_report(
            start_date=self.today.isoformat(),
            end_date=self.today.isoformat(),
            location_id=self.location["id"],
        )
        self.assertGreaterEqual(revenue["revenue"], 27.5)
        outstanding = self.system.outstanding_balances()
        self.assertTrue(all(row["balance_due"] >= 0 for row in outstanding))
        xero_payload = self.system.export_for_xero(invoice_id=invoice["id"])
        self.assertEqual(xero_payload["Contact"]["Name"], "Jordan River")

        calendar = self.system.calendar_view(
            location_id=self.location["id"], target_date=self.today.isoformat()
        )
        self.assertIn(self.today.isoformat(), calendar["bookings"])

    def test_vaccination_required(self) -> None:
        past_expiry = (self.today - dt.timedelta(days=1)).isoformat()
        pet = self.system.add_pet(client_id=self.client["id"], name="Nova")
        self.system.record_vaccination(
            pet_id=pet["id"], vaccine_name="C5", expiry_date=past_expiry
        )
        start = dt.datetime.combine(self.today, dt.time(9, 0)).isoformat()
        end = dt.datetime.combine(self.today, dt.time(11, 0)).isoformat()
        with self.assertRaises(ValidationError):
            self.system.create_booking(
                location_id=self.location["id"],
                client_id=self.client["id"],
                start_time=start,
                end_time=end,
                pet_ids=[pet["id"]],
            )


if __name__ == "__main__":
    unittest.main()
