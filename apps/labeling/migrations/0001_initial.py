import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("rooms", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("input_payload", models.JSONField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("in_progress", "In progress"), ("submitted", "Submitted")], default="pending", max_length=16)),
                ("assigned_at", models.DateTimeField(blank=True, null=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_tasks", to=settings.AUTH_USER_MODEL)),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to="rooms.room")),
            ],
            options={"ordering": ("id",)},
        ),
        migrations.CreateModel(
            name="Annotation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("result_payload", models.JSONField()),
                ("submitted_at", models.DateTimeField()),
                ("annotator", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="annotations", to=settings.AUTH_USER_MODEL)),
                ("task", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="annotation", to="labeling.task")),
            ],
            options={"ordering": ("-submitted_at", "-id")},
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["room", "status"], name="labeling_ta_room_id_6d057b_idx"),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["assigned_to", "status"], name="labeling_ta_assigne_4929ab_idx"),
        ),
    ]
