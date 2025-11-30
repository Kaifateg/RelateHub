from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (ContactRequestViewSet, DiscoverListAPIView,
                    MatchListViewSet, SwipeViewSet)

router = DefaultRouter()
router.register(r"swipes", SwipeViewSet, basename="swipe")
router.register(r"matches", MatchListViewSet, basename="match")
router.register(r"contact-requests", ContactRequestViewSet, basename="contact-request")

urlpatterns = [
    path("", include(router.urls)),
    path("discover/", DiscoverListAPIView.as_view(), name="discover-list"),
]
