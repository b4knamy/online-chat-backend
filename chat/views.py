
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from chat.models import Room
from chat.serializers import RoomSerializer


class ChatRooms(APIView):

    def get(self, request):
        rooms = Room.objects.all()
        rooms_serializer = RoomSerializer(rooms, many=True)
        return Response(rooms_serializer.data, status=status.HTTP_200_OK)
