from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("backdriving", views.backdriving, name="backdriving"),
    path("wp/<int:wp_id>", views.waypoint_detail, name="waypoint_detail"),
    path("create", views.create_toolpath, name="create_toolpath")
]