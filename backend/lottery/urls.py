from django.urls import path

from .views import DrawView, LotteryView


urlpatterns = [
    path("lottery/", LotteryView.as_view(), name="lottery"),
    path("draw/", DrawView.as_view(), name="draw"),
]

