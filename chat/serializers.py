from rest_framework import serializers

from chat.models import Room, Messages, User

# class UserMessageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ("id", "username", "has_room",)


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ("id", "username", "has_room",)


class MessageSerializer(serializers.ModelSerializer):

    user = UserSerializer()

    class Meta:
        model = Messages
        fields = ("id", "user", "text", "created_at",)


class RoomSerializer(serializers.ModelSerializer):

    room_messages = MessageSerializer(many=True)
    admin = UserSerializer()

    class Meta:
        model = Room
        fields = ("id", "admin", "name", "room_messages",)
