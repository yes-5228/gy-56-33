from rest_framework import viewsets

from apps.routes.models import TravelRoute

from .models import Booking
from .serializers import BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer

    def get_queryset(self):
        queryset = Booking.objects.select_related("route").all()
        route_id = self.request.query_params.get("route")
        status = self.request.query_params.get("status")
        if route_id:
            queryset = queryset.filter(route_id=route_id)
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def perform_create(self, serializer):
        booking = serializer.save()
        booking.route = TravelRoute.objects.get(pk=booking.route_id)

    def perform_update(self, serializer):
        booking = serializer.save()
        booking.route = TravelRoute.objects.get(pk=booking.route_id)
