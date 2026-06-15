from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.attractions.models import Attraction
from apps.bookings.models import Booking
from apps.routes.models import RouteStop, TravelRoute


class TravelRouteBudgetTests(TestCase):
    def setUp(self):
        self.attraction1 = Attraction.objects.create(
            name="西湖苏堤",
            city="杭州",
            category="nature",
            duration_hours=Decimal("2.5"),
            ticket_price=Decimal("0"),
            highlight="湖景步道",
            sort_order=1,
        )
        self.attraction2 = Attraction.objects.create(
            name="灵隐寺",
            city="杭州",
            category="culture",
            duration_hours=Decimal("2.0"),
            ticket_price=Decimal("75.00"),
            highlight="古刹祈福",
            sort_order=2,
        )
        self.attraction3 = Attraction.objects.create(
            name="宋城景区",
            city="杭州",
            category="family",
            duration_hours=Decimal("3.5"),
            ticket_price=Decimal("320.00"),
            highlight="沉浸式演艺",
            sort_order=3,
        )
        self.route = TravelRoute.objects.create(
            title="杭州湖山文化 2 日游",
            city="杭州",
            days=2,
            transport="高铁往返 + 市内巴士",
            hotel_level="舒适型四星酒店",
            min_group_size=6,
            max_group_size=18,
            base_cost=Decimal("980.00"),
            guide_fee=Decimal("120.00"),
            status="draft",
            description="串联西湖、灵隐寺与宋城演艺",
        )

    def test_ticket_total_no_stops(self):
        self.assertEqual(self.route.ticket_total, 0)

    def test_ticket_total_with_stops(self):
        RouteStop.objects.create(
            route=self.route,
            attraction=self.attraction1,
            day=1,
            order=1,
        )
        RouteStop.objects.create(
            route=self.route,
            attraction=self.attraction2,
            day=1,
            order=2,
        )
        RouteStop.objects.create(
            route=self.route,
            attraction=self.attraction3,
            day=2,
            order=1,
        )
        expected = Decimal("0") + Decimal("75.00") + Decimal("320.00")
        self.assertEqual(self.route.ticket_total, expected)

    def test_ticket_total_with_free_attractions(self):
        RouteStop.objects.create(
            route=self.route,
            attraction=self.attraction1,
            day=1,
            order=1,
        )
        self.assertEqual(self.route.ticket_total, Decimal("0"))

    def test_estimated_cost_no_stops(self):
        expected = Decimal("980.00") + Decimal("120.00")
        self.assertEqual(self.route.estimated_cost, expected)

    def test_estimated_cost_with_stops(self):
        RouteStop.objects.create(
            route=self.route,
            attraction=self.attraction2,
            day=1,
            order=1,
        )
        RouteStop.objects.create(
            route=self.route,
            attraction=self.attraction3,
            day=2,
            order=1,
        )
        expected = Decimal("980.00") + Decimal("120.00") + Decimal("75.00") + Decimal("320.00")
        self.assertEqual(self.route.estimated_cost, expected)

    def test_estimated_cost_zero_guide_fee(self):
        route = TravelRoute.objects.create(
            title="自由行",
            city="杭州",
            days=1,
            transport="自行前往",
            hotel_level="无",
            min_group_size=2,
            max_group_size=10,
            base_cost=Decimal("500.00"),
            guide_fee=Decimal("0"),
        )
        RouteStop.objects.create(
            route=route,
            attraction=self.attraction2,
            day=1,
            order=1,
        )
        expected = Decimal("500.00") + Decimal("0") + Decimal("75.00")
        self.assertEqual(route.estimated_cost, expected)

    def test_api_response_includes_estimated_cost(self):
        client = APIClient()
        response = client.get(f"/api/routes/{self.route.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("estimated_cost", response.data)
        self.assertIn("ticket_total", response.data)
        expected = Decimal("980.00") + Decimal("120.00")
        self.assertEqual(Decimal(str(response.data["estimated_cost"])), expected)


class TravelRouteEnrolledCountTests(TestCase):
    def setUp(self):
        self.route = TravelRoute.objects.create(
            title="杭州湖山文化 2 日游",
            city="杭州",
            days=2,
            transport="高铁往返",
            hotel_level="四星酒店",
            min_group_size=6,
            max_group_size=18,
            base_cost=Decimal("980.00"),
            guide_fee=Decimal("120.00"),
            status="forming",
        )

    def test_enrolled_count_no_bookings(self):
        self.assertEqual(self.route.enrolled_count, 0)

    def test_enrolled_count_single_booking(self):
        Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=3,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.assertEqual(self.route.enrolled_count, 3)

    def test_enrolled_count_multiple_bookings(self):
        Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=3,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        Booking.objects.create(
            route=self.route,
            contact_name="王先生",
            phone="13800000002",
            party_size=2,
            travel_date=date.today() + timedelta(days=14),
            status="pending",
        )
        Booking.objects.create(
            route=self.route,
            contact_name="张女士",
            phone="13800000003",
            party_size=4,
            travel_date=date.today() + timedelta(days=14),
            status="pending",
        )
        self.assertEqual(self.route.enrolled_count, 9)

    def test_enrolled_count_excludes_cancelled(self):
        Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=3,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        Booking.objects.create(
            route=self.route,
            contact_name="王先生",
            phone="13800000002",
            party_size=2,
            travel_date=date.today() + timedelta(days=14),
            status="cancelled",
        )
        self.assertEqual(self.route.enrolled_count, 3)

    def test_enrolled_count_all_cancelled(self):
        Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=3,
            travel_date=date.today() + timedelta(days=14),
            status="cancelled",
        )
        Booking.objects.create(
            route=self.route,
            contact_name="王先生",
            phone="13800000002",
            party_size=2,
            travel_date=date.today() + timedelta(days=14),
            status="cancelled",
        )
        self.assertEqual(self.route.enrolled_count, 0)

    def test_api_response_includes_enrolled_count(self):
        Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=3,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        client = APIClient()
        response = client.get(f"/api/routes/{self.route.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("enrolled_count", response.data)
        self.assertEqual(response.data["enrolled_count"], 3)


class TravelRouteGroupProgressTests(TestCase):
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

    def test_group_progress_zero_enrolled(self):
        self.assertEqual(self.route.group_progress, 0)

    def test_group_progress_half_way(self):
        Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=5,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.assertEqual(self.route.group_progress, 50)

    def test_group_progress_exactly_full(self):
        Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=10,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.assertEqual(self.route.group_progress, 100)

    def test_group_progress_over_cap_capped_at_100(self):
        Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=15,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.assertEqual(self.route.group_progress, 100)

    def test_group_progress_cancelled_bookings_not_counted(self):
        Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=8,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        Booking.objects.create(
            route=self.route,
            contact_name="王先生",
            phone="13800000002",
            party_size=5,
            travel_date=date.today() + timedelta(days=14),
            status="cancelled",
        )
        self.assertEqual(self.route.group_progress, 80)

    def test_group_progress_zero_min_size(self):
        route = TravelRoute.objects.create(
            title="自由行",
            city="杭州",
            days=1,
            transport="自行前往",
            hotel_level="无",
            min_group_size=0,
            max_group_size=10,
            base_cost=Decimal("500.00"),
            guide_fee=Decimal("0"),
        )
        self.assertEqual(route.group_progress, 100)

    def test_group_progress_rounding(self):
        route = TravelRoute.objects.create(
            title="测试团",
            city="杭州",
            days=1,
            transport="大巴",
            hotel_level="无",
            min_group_size=3,
            max_group_size=10,
            base_cost=Decimal("100.00"),
            guide_fee=Decimal("0"),
        )
        Booking.objects.create(
            route=route,
            contact_name="测试",
            phone="13900000000",
            party_size=1,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.assertEqual(route.group_progress, 33)

    def test_api_response_includes_group_progress(self):
        Booking.objects.create(
            route=self.route,
            contact_name="李女士",
            phone="13800000001",
            party_size=5,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        client = APIClient()
        response = client.get(f"/api/routes/{self.route.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("group_progress", response.data)
        self.assertEqual(response.data["group_progress"], 50)


class TravelRouteListBudgetAndProgressTests(TestCase):
    def setUp(self):
        self.attraction = Attraction.objects.create(
            name="灵隐寺",
            city="杭州",
            category="culture",
            duration_hours=Decimal("2.0"),
            ticket_price=Decimal("75.00"),
            highlight="古刹",
            sort_order=1,
        )
        self.route1 = TravelRoute.objects.create(
            title="线路一",
            city="杭州",
            days=2,
            transport="高铁",
            hotel_level="四星",
            min_group_size=10,
            max_group_size=20,
            base_cost=Decimal("500.00"),
            guide_fee=Decimal("50.00"),
            status="forming",
        )
        RouteStop.objects.create(
            route=self.route1,
            attraction=self.attraction,
            day=1,
            order=1,
        )
        Booking.objects.create(
            route=self.route1,
            contact_name="A",
            phone="13800000001",
            party_size=5,
            travel_date=date.today() + timedelta(days=14),
            status="confirmed",
        )
        self.route2 = TravelRoute.objects.create(
            title="线路二",
            city="南京",
            days=1,
            transport="大巴",
            hotel_level="无",
            min_group_size=4,
            max_group_size=10,
            base_cost=Decimal("200.00"),
            guide_fee=Decimal("20.00"),
            status="draft",
        )

    def test_list_includes_budget_and_progress(self):
        client = APIClient()
        response = client.get("/api/routes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

        route1_data = next(r for r in response.data if r["id"] == self.route1.id)
        self.assertIn("estimated_cost", route1_data)
        self.assertIn("ticket_total", route1_data)
        self.assertIn("enrolled_count", route1_data)
        self.assertIn("group_progress", route1_data)
        self.assertEqual(route1_data["enrolled_count"], 5)
        self.assertEqual(route1_data["group_progress"], 50)

        route2_data = next(r for r in response.data if r["id"] == self.route2.id)
        self.assertEqual(route2_data["enrolled_count"], 0)
        self.assertEqual(route2_data["group_progress"], 0)
