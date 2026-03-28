import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def populate_task_assignments(apps, schema_editor):
    Task = apps.get_model("labeling", "Task")
    Annotation = apps.get_model("labeling", "Annotation")
    TaskAssignment = apps.get_model("labeling", "TaskAssignment")
    db_alias = schema_editor.connection.alias

    for task in Task.objects.using(db_alias).all().iterator():
        annotation = Annotation.objects.using(db_alias).filter(task_id=task.id).first()
        if annotation:
            submitted_at = annotation.submitted_at
            assigned_at = task.assigned_at or submitted_at or task.updated_at or task.created_at
            assignment = TaskAssignment.objects.using(db_alias).create(
                task_id=task.id,
                annotator_id=annotation.annotator_id,
                round_number=1,
                status="submitted",
                assigned_at=assigned_at,
                submitted_at=submitted_at,
            )
            Annotation.objects.using(db_alias).filter(id=annotation.id).update(assignment_id=assignment.id)
            Task.objects.using(db_alias).filter(id=task.id).update(
                status="submitted",
                current_round=1,
                validation_score=100.0,
                consensus_payload=annotation.result_payload,
            )
            continue

        if task.assigned_to_id:
            TaskAssignment.objects.using(db_alias).create(
                task_id=task.id,
                annotator_id=task.assigned_to_id,
                round_number=1,
                status="in_progress",
                assigned_at=task.assigned_at or task.updated_at or task.created_at,
            )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("labeling", "0002_task_source_file_task_source_name_task_source_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="consensus_payload",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="current_round",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="task",
            name="validation_score",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="TaskAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("round_number", models.PositiveIntegerField(default=1)),
                ("status", models.CharField(choices=[("in_progress", "In progress"), ("submitted", "Submitted")], default="in_progress", max_length=16)),
                ("assigned_at", models.DateTimeField()),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("annotator", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="task_assignments", to=settings.AUTH_USER_MODEL)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="labeling.task")),
            ],
            options={
                "ordering": ("task_id", "round_number", "annotator_id"),
            },
        ),
        migrations.AddField(
            model_name="annotation",
            name="assignment",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="annotation", to="labeling.taskassignment"),
        ),
        migrations.AlterField(
            model_name="annotation",
            name="task",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="annotations", to="labeling.task"),
        ),
        migrations.RunPython(populate_task_assignments, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="annotation",
            name="assignment",
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="annotation", to="labeling.taskassignment"),
        ),
        migrations.AddConstraint(
            model_name="annotation",
            constraint=models.UniqueConstraint(fields=("task", "annotator"), name="unique_task_annotator_annotation"),
        ),
        migrations.AddConstraint(
            model_name="taskassignment",
            constraint=models.UniqueConstraint(fields=("task", "annotator"), name="unique_task_assignment_annotator"),
        ),
        migrations.AddIndex(
            model_name="taskassignment",
            index=models.Index(fields=["task", "status"], name="labeling_ta_task_st_4f3f33_idx"),
        ),
        migrations.AddIndex(
            model_name="taskassignment",
            index=models.Index(fields=["annotator", "status"], name="labeling_ta_annota_86cd11_idx"),
        ),
        migrations.AddIndex(
            model_name="taskassignment",
            index=models.Index(fields=["task", "round_number", "status"], name="labeling_ta_task_ro_217969_idx"),
        ),
        migrations.RemoveIndex(
            model_name="task",
            name="labeling_ta_assigne_4929ab_idx",
        ),
        migrations.RemoveField(
            model_name="task",
            name="assigned_at",
        ),
        migrations.RemoveField(
            model_name="task",
            name="assigned_to",
        ),
    ]
