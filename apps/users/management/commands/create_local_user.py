from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


User = get_user_model()


class Command(BaseCommand):
    help = "Create or update a local user for manual testing."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("password")
        parser.add_argument("--email", default="")
        parser.add_argument("--staff", action="store_true")
        parser.add_argument("--superuser", action="store_true")

    def handle(self, *args, **options):
        username = options["username"].strip()
        password = options["password"]
        email = options["email"].strip()

        if not username:
            raise CommandError("Username must not be empty.")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
            },
        )

        if email:
            user.email = email

        user.is_staff = bool(options["staff"] or options["superuser"])
        user.is_superuser = bool(options["superuser"])
        user.set_password(password)
        user.save()

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"User {username!r} {action} successfully."))
