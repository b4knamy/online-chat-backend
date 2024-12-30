from django.contrib import admin

from chat.models import User, Messages, Room

# Register your models here.


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    pass


@admin.register(Messages)
class MessagesAdmin(admin.ModelAdmin):
    pass
