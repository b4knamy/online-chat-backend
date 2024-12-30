
from rest_framework.views import APIView
from django.contrib.auth import authenticate, logout
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from chat.models import Room, User
from chat.serializers import RoomSerializer, UserSerializer


class ChatRooms(APIView):

    def get(self, request):
        rooms = Room.objects.all()
        rooms_serializer = RoomSerializer(rooms, many=True)
        return Response(rooms_serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        room_name = request.data.get("room")

        if room_name:
            user = User.objects.get(username="baknamy")
            new_room = Room.objects.create(
                admin=user,
                name=room_name,
            )
            new_room.save()
            new_room_serializer = RoomSerializer(new_room)

            return Response(new_room_serializer.data, status=status.HTTP_201_CREATED)

        return Response(status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(["POST"])
def login_view(request):

    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response({"error": "Credentials missing."}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)

    if user is not None:
        user_serialized = UserSerializer(user)

        return Response(user_serialized.data, status=status.HTTP_200_OK)

    return Response({"error": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes((IsAuthenticated,))
def logout_view(request):
    logout(request)
    return Response(status=status.HTTP_200_OK)
