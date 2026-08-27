from . import views
from django.urls import path


urlpatterns = [
    path(
        "registers/download_mission/<str:mission_code>/",
        views.download_mission,
        name="download_mission",
    )
]
