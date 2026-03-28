from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0003_room_dataset_type_roomlabel"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="cross_validation_annotators_count",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="room",
            name="cross_validation_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="room",
            name="cross_validation_similarity_threshold",
            field=models.PositiveSmallIntegerField(default=80),
        ),
    ]
