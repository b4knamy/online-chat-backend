from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.


class User(AbstractUser):
    has_room = models.BooleanField(default=False)


class Room(models.Model):
    admin = models.ForeignKey(
        User, related_name="user_room", on_delete=models.CASCADE)
    name = models.CharField(max_length=10)
    max_users = models.IntegerField(default=3)

    def save(self, *args, **kwargs):
        if self.admin and not self.admin.has_room:
            self.admin.has_room = True
            self.admin.save()
        return super().save(*args, **kwargs)


class Messages(models.Model):
    user = models.ForeignKey(
        User, related_name="user_messages", on_delete=models.CASCADE)
    room = models.ForeignKey(
        Room, related_name="room_messages", on_delete=models.CASCADE)
    text = models.TextField("Texto")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Date Created")
