from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.models import Booking
from apps.routes.models import TravelRoute


class BookingCancelTests(TestCase):
    def setUp(self):
        self.route = TravelRoute.objects.create(
            title="杭州湖山文化 2 日游",
            city="杭州",
            days=2,
            transport="高铁往返",
            hotel_level="四星酒店",
            min_group_size=10,
            max_group_size=20,
            base_cost=Decimal("980.00"),
            guide_fee=Decimal("120.00"),
            status="forming",
        )
        self.booking = Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=3,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )

    def test_cancel_booking_changes_status(self):
        self.assertEqual(self.booking.status, "confirmed")
        self.booking.status = "cancelled"
        self.booking.save()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "cancelled")

    def test_cancel_booking_reduces_enrolled_count(self):
        self.assertEqual(self.route.enrolled_count, 3)
        self.booking.status = "cancelled"
        self.booking.save()
        self.route.refresh_from_db()
        self.assertEqual(self.route.enrolled_count, 0)

    def test_cancel_booking_reduces_group_progress(self):
        self.assertEqual(self.route.group_progress, 30)
        self.booking.status = "cancelled"
        self.booking.save()
        self.route.refresh_from_db()
        self.assertEqual(self.route.group_progress, 0)

    def test_cancel_one_of_multiple_bookings(self):
        booking2 = Booking.objects.create(
            route=self.route,
            contact_name="王先生",
            phone="13800000002",
            party_size=5,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.assertEqual(self.route.enrolled_count, 8)
        self.assertEqual(self.route.group_progress, 80)

        self.booking.status = "cancelled"
        self.booking.save()
        self.route.refresh_from_db()

        self.assertEqual(self.route.enrolled_count, 5)
        self.assertEqual(self.route.group_progress, 50)

    def test_cancel_pending_booking(self):
        pending_booking = Booking.objects.create(
            route=self.route,
            contact_name="张女士",
            phone="13800000003",
            party_size=2,
            travel_date=date.today() + timedelta(days=14),
            status="pending",
        )
        self.assertEqual(self.route.enrolled_count, 5)
        self.assertEqual(self.route.group_progress, 50)

        pending_booking.status = "cancelled"
        pending_booking.save()
        self.route.refresh_from_db()

        self.assertEqual(self.route.enrolled_count, 3)
        self.assertEqual(self.route.group_progress, 30)


class BookingAPICancelTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.route = TravelRoute.objects.create(
            title="杭州湖山文化 2 日游",
            city="杭州",
            days=2,
            transport="高铁往返",
            hotel_level="四星酒店",
            min_group_size=10,
            max_group_size=20,
            base_cost=Decimal("980.00"),
            guide_fee=Decimal("120.00"),
            status="forming",
        )
        self.booking = Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=3,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )

    def test_api_cancel_booking_via_patch(self):
        response = self.client.patch(
            f"/api/bookings/{self.booking.id}/",
            {"status": "cancelled"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "cancelled")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "cancelled")

    def test_api_cancel_updates_route_progress(self):
        response = self.client.patch(
            f"/api/bookings/{self.booking.id}/",
            {"status": "cancelled"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["group_enrolled"], 0)
        self.assertEqual(response.data["group_progress"], 0)

    def test_api_booking_detail_includes_group_info(self):
        response = self.client.get(f"/api/bookings/{self.booking.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("group_enrolled", response.data)
        self.assertIn("min_group_size", response.data)
        self.assertIn("group_progress", response.data)
        self.assertEqual(response.data["group_enrolled"], 3)
        self.assertEqual(response.data["min_group_size"], 10)
        self.assertEqual(response.data["group_progress"], 30)

    def test_api_booking_list_includes_group_info(self):
        response = self.client.get("/api/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        booking_data = response.data[0]
        self.assertIn("group_enrolled", booking_data)
        self.assertIn("group_progress", booking_data)
        self.assertEqual(booking_data["group_enrolled"], 3)
        self.assertEqual(booking_data["group_progress"], 30)

    def test_api_filter_bookings_by_status_cancelled(self):
        Booking.objects.create(
            route=self.route,
            contact_name="王先生",
            phone="13800000002",
            party_size=2,
            travel_date=date.today() + timedelta(days=14),
            status="cancelled",
        )
        response = self.client.get("/api/bookings/?status=cancelled")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["contact_name"], "王先生")

    def test_api_filter_bookings_by_status_pending(self):
        Booking.objects.create(
            route=self.route,
            contact_name="张女士",
            phone="13800000003",
            party_size=4,
            travel_date=date.today() + timedelta(days=14),
            status="pending",
        )
        response = self.client.get("/api/bookings/?status=pending")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["contact_name"], "张女士")


class BookingEnrollmentImpactTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.route = TravelRoute.objects.create(
            title="杭州湖山文化 2 日游",
            city="杭州",
            days=2,
            transport="高铁往返",
            hotel_level="四星酒店",
            min_group_size=10,
            max_group_size=20,
            base_cost=Decimal("980.00"),
            guide_fee=Decimal("120.00"),
            status="forming",
        )

    def test_create_booking_increases_enrolled_count(self):
        self.assertEqual(self.route.enrolled_count, 0)
        response = self.client.post(
            "/api/bookings/",
            {
                "route": self.route.id,
                "contact_name": "李女士",
                "phone": "13800000001",
                "party_size": 3,
                "travel_date": str(date.today() + timedelta(days=14)),
                "status": "confirmed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.route.refresh_from_db()
        self.assertEqual(self.route.enrolled_count, 3)

    def test_create_booking_increases_group_progress(self):
        self.assertEqual(self.route.group_progress, 0)
        self.client.post(
            "/api/bookings/",
            {
                "route": self.route.id,
                "contact_name": "李女士",
                "phone": "13800000001",
                "party_size": 5,
                "travel_date": str(date.today() + timedelta(days=14)),
                "status": "confirmed",
            },
            format="json",
        )
        self.route.refresh_from_db()
        self.assertEqual(self.route.group_progress, 50)

    def test_update_party_size_changes_enrolled_count(self):
        booking = Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=3,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.assertEqual(self.route.enrolled_count, 3)

        response = self.client.patch(
            f"/api/bookings/{booking.id}/",
            {"party_size": 5},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.route.refresh_from_db()
        self.assertEqual(self.route.enrolled_count, 5)

    def test_update_party_size_changes_group_progress(self):
        booking = Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=3,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.assertEqual(self.route.group_progress, 30)

        self.client.patch(
            f"/api/bookings/{booking.id}/",
            {"party_size": 5},
            format="json",
        )
        self.route.refresh_from_db()
        self.assertEqual(self.route.group_progress, 50)

    def test_cancelled_booking_not_counted_in_enrolled(self):
        booking = Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=5,
            travel_date=date.today() + timedelta(days=14),
            status="cancelled",
        )
        self.assertEqual(self.route.enrolled_count, 0)
        self.assertEqual(self.route.group_progress, 0)

    def test_full_group_shows_100_percent_progress(self):
        Booking.objects.create(
            route=self.route,
            contact_name="A",
            phone="13800000001",
            party_size=10,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.assertEqual(self.route.group_progress, 100)

    def test_over_min_group_still_100_percent(self):
        Booking.objects.create(
            route=self.route,
            contact_name="A",
            phone="13800000001",
            party_size=15,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.assertEqual(self.route.group_progress, 100)

    def test_api_route_details_after_booking_changes(self):
        booking = Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=5,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )

        response = self.client.get(f"/api/routes/{self.route.id}/")
        self.assertEqual(response.data["enrolled_count"], 5)
        self.assertEqual(response.data["group_progress"], 50)

        self.client.patch(
            f"/api/bookings/{booking.id}/",
            {"status": "cancelled"},
            format="json",
        )

        response = self.client.get(f"/api/routes/{self.route.id}/")
        self.assertEqual(response.data["enrolled_count"], 0)
        self.assertEqual(response.data["group_progress"], 0)


class BookingCapacityValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.route = TravelRoute.objects.create(
            title="小团测试",
            city="杭州",
            days=1,
            transport="大巴",
            hotel_level="无",
            min_group_size=4,
            max_group_size=6,
            base_cost=Decimal("100.00"),
            guide_fee=Decimal("0"),
            status="forming",
        )
        Booking.objects.create(
            route=self.route,
            contact_name="A",
            phone="13800000001",
            party_size=4,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )

    def test_create_booking_within_capacity_succeeds(self):
        response = self.client.post(
            "/api/bookings/",
            {
                "route": self.route.id,
                "contact_name": "B",
                "phone": "13800000002",
                "party_size": 2,
                "travel_date": str(date.today() + timedelta(days=14)),
                "status": "confirmed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.route.refresh_from_db()
        self.assertEqual(self.route.enrolled_count, 6)

    def test_create_booking_exceeding_capacity_fails(self):
        response = self.client.post(
            "/api/bookings/",
            {
                "route": self.route.id,
                "contact_name": "B",
                "phone": "13800000002",
                "party_size": 3,
                "travel_date": str(date.today() + timedelta(days=14)),
                "status": "confirmed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.route.refresh_from_db()
        self.assertEqual(self.route.enrolled_count, 4)

    def test_create_booking_exactly_at_capacity_succeeds(self):
        response = self.client.post(
            "/api/bookings/",
            {
                "route": self.route.id,
                "contact_name": "B",
                "phone": "13800000002",
                "party_size": 2,
                "travel_date": str(date.today() + timedelta(days=14)),
                "status": "pending",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_create_cancelled_booking_bypasses_capacity_check(self):
        response = self.client.post(
            "/api/bookings/",
            {
                "route": self.route.id,
                "contact_name": "B",
                "phone": "13800000002",
                "party_size": 10,
                "travel_date": str(date.today() + timedelta(days=14)),
                "status": "cancelled",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.route.refresh_from_db()
        self.assertEqual(self.route.enrolled_count, 4)

    def test_update_party_size_exceeding_capacity_fails(self):
        booking = Booking.objects.create(
            route=self.route,
            contact_name="B",
            phone="13800000002",
            party_size=2,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        response = self.client.patch(
            f"/api/bookings/{booking.id}/",
            {"party_size": 3},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cancel_to_confirmed_within_capacity_succeeds(self):
        cancelled_booking = Booking.objects.create(
            route=self.route,
            contact_name="C",
            phone="13800000003",
            party_size=2,
            travel_date=date.today() + timedelta(days=14),
            status="cancelled",
        )
        response = self.client.patch(
            f"/api/bookings/{cancelled_booking.id}/",
            {"status": "confirmed"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "confirmed")
        self.route.refresh_from_db()
        self.assertEqual(self.route.enrolled_count, 6)

    def test_cancel_to_confirmed_exceeding_capacity_fails(self):
        cancelled_booking = Booking.objects.create(
            route=self.route,
            contact_name="C",
            phone="13800000003",
            party_size=5,
            travel_date=date.today() + timedelta(days=14),
            status="cancelled",
        )
        response = self.client.patch(
            f"/api/bookings/{cancelled_booking.id}/",
            {"status": "confirmed"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        cancelled_booking.refresh_from_db()
        self.assertEqual(cancelled_booking.status, "cancelled")

    def test_api_response_includes_max_group_size(self):
        response = self.client.get("/api/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("max_group_size", response.data[0])
        self.assertEqual(response.data[0]["max_group_size"], 6)


class BookingRestoreSyncTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.route = TravelRoute.objects.create(
            title="恢复测试线路",
            city="杭州",
            days=1,
            transport="大巴",
            hotel_level="无",
            min_group_size=10,
            max_group_size=20,
            base_cost=Decimal("100.00"),
            guide_fee=Decimal("0"),
            status="forming",
        )
        self.booking = Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=5,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )

    def test_restore_cancelled_booking_updates_enrolled_in_response(self):
        self.client.patch(
            f"/api/bookings/{self.booking.id}/",
            {"status": "cancelled"},
            format="json",
        )
        cancel_response = self.client.get(f"/api/bookings/{self.booking.id}/")
        self.assertEqual(cancel_response.data["group_enrolled"], 0)
        self.assertEqual(cancel_response.data["group_progress"], 0)

        restore_response = self.client.patch(
            f"/api/bookings/{self.booking.id}/",
            {"status": "confirmed"},
            format="json",
        )
        self.assertEqual(restore_response.status_code, 200)
        self.assertEqual(restore_response.data["status"], "confirmed")
        self.assertEqual(restore_response.data["group_enrolled"], 5)
        self.assertEqual(restore_response.data["group_progress"], 50)

    def test_restore_cancelled_booking_updates_route_detail(self):
        self.client.patch(
            f"/api/bookings/{self.booking.id}/",
            {"status": "cancelled"},
            format="json",
        )

        self.client.patch(
            f"/api/bookings/{self.booking.id}/",
            {"status": "confirmed"},
            format="json",
        )

        route_response = self.client.get(f"/api/routes/{self.route.id}/")
        self.assertEqual(route_response.data["enrolled_count"], 5)
        self.assertEqual(route_response.data["group_progress"], 50)

    def test_restore_one_of_several_cancelled_bookings(self):
        booking2 = Booking.objects.create(
            route=self.route,
            contact_name="王先生",
            phone="13800000002",
            party_size=3,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.client.patch(
            f"/api/bookings/{self.booking.id}/",
            {"status": "cancelled"},
            format="json",
        )
        self.client.patch(
            f"/api/bookings/{booking2.id}/",
            {"status": "cancelled"},
            format="json",
        )

        self.assertEqual(self.route.enrolled_count, 0)
        self.assertEqual(self.route.group_progress, 0)

        self.client.patch(
            f"/api/bookings/{booking2.id}/",
            {"status": "confirmed"},
            format="json",
        )
        self.route.refresh_from_db()
        self.assertEqual(self.route.enrolled_count, 3)
        self.assertEqual(self.route.group_progress, 30)

    def test_restore_to_pending_also_counts(self):
        self.client.patch(
            f"/api/bookings/{self.booking.id}/",
            {"status": "cancelled"},
            format="json",
        )
        response = self.client.patch(
            f"/api/bookings/{self.booking.id}/",
            {"status": "pending"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["group_enrolled"], 5)
        self.assertEqual(response.data["group_progress"], 50)
