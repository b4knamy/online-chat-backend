from django.urls import path
from .views import ChatRooms

urlpatterns = [
    path("rooms", ChatRooms.as_view(), name="chat-rooms"),
]
