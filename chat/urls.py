from django.urls import path
from .views import ChatRooms, login_view, logout_view

urlpatterns = [
    path("rooms", ChatRooms.as_view(), name="chat-rooms"),
    path("auth/login", login_view, name="login-view"),
    path("auth/logout", logout_view, name="logout-view"),
]
