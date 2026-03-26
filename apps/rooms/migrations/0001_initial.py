import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Room",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="created_rooms", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at", "-id")},
        ),
        migrations.CreateModel(
            name="RoomMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("invited", "Invited"), ("joined", "Joined")], default="invited", max_length=16)),
                ("joined_at", models.DateTimeField(blank=True, null=True)),
                ("invited_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_room_invitations", to=settings.AUTH_USER_MODEL)),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="rooms.room")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="room_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("room_id", "user_id")},
        ),
        migrations.AddConstraint(
            model_name="roommembership",
            constraint=models.UniqueConstraint(fields=("room", "user"), name="unique_room_membership"),
        ),
    ]
