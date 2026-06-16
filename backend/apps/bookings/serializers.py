from rest_framework import serializers

from apps.routes.models import TravelRoute

from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    route_title = serializers.CharField(source="route.title", read_only=True)
    route_city = serializers.CharField(source="route.city", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    group_enrolled = serializers.IntegerField(source="route.enrolled_count", read_only=True)
    min_group_size = serializers.IntegerField(source="route.min_group_size", read_only=True)
    max_group_size = serializers.IntegerField(source="route.max_group_size", read_only=True)
    group_progress = serializers.IntegerField(source="route.group_progress", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "route",
            "route_title",
            "route_city",
            "contact_name",
            "phone",
            "party_size",
            "travel_date",
            "status",
            "status_label",
            "remark",
            "group_enrolled",
            "min_group_size",
            "max_group_size",
            "group_progress",
            "created_at",
        ]

    def validate(self, attrs):
        route = self._resolve_route(attrs)
        if route is None:
            return attrs

        party_size = attrs.get("party_size", self.instance.party_size if self.instance else 1)
        new_status = attrs.get("status", self.instance.status if self.instance else "pending")

        if new_status == "cancelled":
            return attrs

        current_enrolled = self._current_enrolled_excluding_self(route)
        if current_enrolled + party_size > route.max_group_size:
            raise serializers.ValidationError(
                f"报名人数超出上限：当前已报 {current_enrolled} 人，本单 {party_size} 人，"
                f"线路最多 {route.max_group_size} 人"
            )

        return attrs

    def _resolve_route(self, attrs):
        if self.instance:
            return self.instance.route
        route_id = attrs.get("route")
        if route_id is None:
            return None
        if isinstance(route_id, TravelRoute):
            return route_id
        try:
            return TravelRoute.objects.get(pk=route_id)
        except TravelRoute.DoesNotExist:
            return None

    def _current_enrolled_excluding_self(self, route):
        qs = route.bookings.exclude(status="cancelled")
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        return sum(b.party_size for b in qs)
