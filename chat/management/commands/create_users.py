from django.core.management import BaseCommand
from django.core.management.base import CommandParser
from django.contrib.auth.hashers import make_password
from chat.models import User


class Command(BaseCommand):

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--og", action="store_true")

    def handle(self, *args, **kwargs):
        usernames = ["Basch", "Vaan", "Fran", "Ashe", "Penelo", "Balthier"]
        password = make_password("fkUser10@!")
        for username in usernames:
            new_user = User.objects.create(
                username=username,
                password=password
            )
            new_user.save()

        self.stdout.write(self.style.SUCCESS("Usuários criados!"))
