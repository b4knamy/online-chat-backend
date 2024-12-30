import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.auth import login, logout
import redis.client
from .models import Room, Messages, User
from django.core.cache import cache
import redis

redis_client = redis.StrictRedis()

usernames = [user.username for user in User.objects.all()]
redis_client.sadd("available_users", *usernames)
redis_client.set("online_count", 0)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        self.last_message_date = ""

        try:
            self.room_object = await Room.objects.aget(name=self.room_name)
            self.current_user = await User.objects.aget(username="baknamy")
        except Room.DoesNotExist:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        body = json.loads(text_data)
        text = body.get("text")

        message_id = await self.save_chat_context(text)

        context = {
            "id": message_id,
            "text": text,
            "user": {
                "id": self.current_user.id,
                "username": self.current_user.username,
            },
            "created_at": self.last_message_date,
        }

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {
                "type": "chat.message", "data": {"message": context}}
        )

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))

    async def save_chat_context(self, text):

        message_object = await Messages.objects.acreate(
            user=self.current_user,
            room=self.room_object,
            text=text,
        )
        self.last_message_date = message_object.created_at.strftime("%d/%m/%Y")
        await message_object.asave()
        return message_object.id


class EnvironmentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_context_name = "rooms_group"
        self.users_context_name = "users_group"
        self.redis_users_key = "available_users"
        self.redis_online_key = "online_count"

        await self.channel_layer.group_add(self.room_context_name, self.channel_name)
        await self.channel_layer.group_add(self.users_context_name, self.channel_name)
        await self.accept()

        await self.show_available_users()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_context_name, self.channel_name)
        await self.channel_layer.group_discard(self.users_context_name, self.channel_name)

        await self.logout_user()

    async def receive(self, text_data):
        body = json.loads(text_data)
        event_type = body["type"]
        print(body)
        if event_type == "login.user":
            username = body["data"]["username"]
            await self.login_user(username)
        else:
            new_room = body["data"]["new_room"]
            new_room_id = await self.create_new_room(new_room)
            context = {
                "admin": {
                    "id": self.current_user.id,
                    "username": self.current_user.username,
                },
                "id": new_room_id,
                "name": new_room,
                "room_messages": [],
            }

            await self.channel_layer.group_send(
                self.room_context_name, {
                    "type": "room.created",
                    "data": {
                        "room": context
                    },
                }
            )

    async def room_created(self, event):
        await self.send(
            text_data=json.dumps(event)
        )

    async def create_new_room(self, room_name: str) -> int:
        new_room: Room = await Room.objects.acreate(
            admin=self.current_user,
            name=room_name,
        )
        await new_room.asave()
        return new_room.id

    async def show_available_users(self) -> None:
        available_users = await self.get_available_users()
        online_users = await self.get_online_users_count()
        print(online_users)
        print(f"\n\n{available_users}\n\n")

        await self.channel_layer.group_send(
            self.users_context_name, {
                "type": "available.users",
                "data": {
                    "available_users": available_users,
                    "online_users": online_users,
                },
            }
        )

    async def available_users(self, event):

        await self.send(text_data=json.dumps(event))

    async def login_user(self, username: str) -> None:
        available_users = await self.get_available_users()
        if username in available_users:
            redis_client.srem(self.redis_users_key, username)
            user = await User.objects.aget(username=username)
            await login(self.scope, user)

            online_users = await self.get_online_users_count()
            redis_client.set(self.redis_online_key, online_users + 1)

            await self.show_available_users()

            print(f"\n User {username} is logged in now! \n")
        else:
            print("\n\nuser selected is not available!\n\n")

    async def logout_user(self):
        username = self.scope["user"].username
        print(self.scope["user"])
        redis_client.sadd(self.redis_users_key, username)
        print(f"username: {username} was added")
        await logout(self.scope)
        online_users = await self.get_online_users_count()
        if online_users > 0:
            redis_client.set(self.redis_online_key, online_users - 1)
        await self.show_available_users()
        print(f"\n User {username} is logged out now! \n")

    async def get_available_users(self):
        return [username.decode(
            "utf-8") for username in redis_client.smembers(self.redis_users_key)]

    async def get_online_users_count(self):
        return int(redis_client.get(self.redis_online_key))
