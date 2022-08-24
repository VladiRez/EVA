from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("backdriving", views.backdriving, name="backdriving"),
    path("wp/<str:wp_id>", views.waypoint_detail, name="waypoint_detail"),
    path("tp", views.toolpath_index, name="toolpath_index"),
    path("tp/<str:tp_id>", views.toolpath_detail, name="toolpath_detail")
]