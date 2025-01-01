import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.auth import login, logout
from django.db.utils import IntegrityError
from re import match
import redis.client
from .models import Room, Messages, User
import redis

redis_client = redis.StrictRedis()
usernames = [
    user.username for user in User.objects.filter(is_superuser=False)]
# usernames = [
#     user.username for user in User.objects.all()]
redis_client.sadd("available_users", *usernames)
redis_client.set("online_count", 0)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        self.last_message_date = ""
        query_strings = parse_qs(self.scope["query_string"].decode("utf-8"))
        username = query_strings.get("username", [""])[0]

        try:
            self.room_object = await Room.objects.aget(name=self.room_name)
            self.current_user = await User.objects.aget(username=username)
        except (Room.DoesNotExist, User.DoesNotExist):
            await self.close()
            return

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

        await self.channel_layer.group_send(
            self.room_group_name, {
                "type": "chat.message", "data": {"message": context}}
        )

    async def chat_message(self, event):
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

    # defaults

    async def connect(self) -> None:
        self.environment_group = "environment_group"
        self.redis_users_key = "available_users"
        self.redis_online_key = "online_count"

        await self.channel_layer.group_add(self.environment_group, self.channel_name)
        await self.accept()

        await self.show_available_users()

    async def disconnect(self, code) -> None:
        await self.channel_layer.group_discard(self.environment_group, self.channel_name)
        await self.logout_user_handler()

    async def receive(self, text_data) -> None:
        body = json.loads(text_data)
        print(body)
        data = body.get("data", None)
        handler = getattr(
            self, f"{body["type"].replace(".", "_")}_handler", None)

        if handler:
            await handler(data)
        else:
            await self.send_warning_message("Something goes wrong...")

    async def event_handler(self, event) -> None:
        await self.send(text_data=json.dumps(event))

    # related_handlers

    async def room_created_handler(self, data: dict) -> None:
        if self.scope["user"].has_room:
            message = f"Usuário {
                self.scope["user"].username} já possui uma sala."
            await self.send_warning_message(message)
            return
        room_name = data["new_room"]

        if not match(r"^[a-zA-Z0-9]{3,10}$", room_name):
            message = "O nome da sala precisa conter entre 3 a 10 caracteres, apenas letras, numeros e sem espaços."
            await self.send_warning_message(message)
            return
        try:
            new_room: Room = await Room.objects.acreate(
                admin=self.scope["user"],
                name=room_name,
            )
            await new_room.asave()
        except IntegrityError:
            message = f"Sala com o nome {room_name} já existe!"
            await self.send_warning_message(message)

        self.scope["user"].has_room = True
        await self.scope["user"].asave()
        context = {
            "admin": {
                "id": self.scope["user"].id,
                "username": self.scope["user"].username,
            },
            "id": new_room.id,
            "name": new_room.name,
            "room_messages": [],
        }
        await self.update_group_context("room.created", context)
        await self.send_notification(f'Usuário {self.scope["user"].username} acabou de criar a sala {room_name}!')

    async def login_user_handler(self, data: dict) -> None:
        username = data["username"]
        available_users = await self.get_available_users()

        if username in available_users:
            user = await User.objects.aget(username=username)
            await login(self.scope, user)
            await self.update_available_users(username, remove=True)
            await self.send_notification(f'Usuário {self.scope["user"].username} entrou!')

    async def logout_user_handler(self, data: dict | None = None) -> None:
        print(f"\n{self.scope["user"].username} is now logged out.\n")
        await logout(self.scope)
        await self.update_available_users(self.scope["user"].username)
        await self.send_notification(f'Usuário {self.scope["user"].username} saiu!')

    async def remove_room_handler(self, data: dict) -> None:
        room = data["room"]
        selected_room = await Room.objects.aget(name=room)
        await selected_room.adelete()
        self.scope["user"].has_room = False
        await self.scope["user"].asave()
        await self.update_group_context("remove.room", {"room": room})
        await self.send_notification(f'Usuário {self.scope["user"].username} deletou a sala {room}!')

    # helpers

    async def get_available_users(self) -> list[str]:
        return [username.decode(
            "utf-8") for username in redis_client.smembers(self.redis_users_key)]

    async def get_online_users_count(self) -> int:
        return int(redis_client.get(self.redis_online_key))

    async def show_available_users(self, online_users: int | None = None) -> None:
        available_users = await self.get_available_users()

        if not online_users:
            online_users = await self.get_online_users_count()

        data = {
            "available_users": available_users,
            "online_users": online_users,
        }
        await self.update_group_context("available.users", data)

    async def send_warning_message(self, message: str):
        context = {
            "event_type": "room.failed",
            "context": {
                "message": message
            }
        }
        print(context)
        await self.send(json.dumps(context))

    async def update_group_context(self, event_type: str, data: dict) -> None:

        await self.channel_layer.group_send(
            self.environment_group, {
                "type": "event.handler",
                "event_type": event_type,
                "context": data
            }
        )

    async def update_available_users(self, username: str, remove=False) -> None:
        online_users = await self.get_online_users_count()
        if remove:
            redis_client.srem(self.redis_users_key, username)
            online_users += 1

        else:
            redis_client.sadd(self.redis_users_key, username)
            if online_users <= 0:
                return
            online_users -= 1

        redis_client.set(self.redis_online_key, online_users)
        await self.show_available_users(online_users)

    async def send_notification(self, message: str) -> None:
        context = {
            "message": message
        }
        await self.update_group_context("notify.user", context)
