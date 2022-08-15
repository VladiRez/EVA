from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("unlocked", views.index, {"reset": True}, name="reset"),
    path("backdriving", views.backdriving, name="backdriving"),
    path("wp/<str:wp_id>", views.waypoint_detail, name="waypoint_detail"),
    path("wp/del/<str:wp_id>", views.waypoint_detail, {"delete": True}, name="waypoint_delete"),
    path("create", views.create_toolpath, name="create_toolpath")
]