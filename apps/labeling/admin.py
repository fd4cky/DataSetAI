from django.contrib import admin

from apps.labeling.models import Annotation, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "status", "assigned_to", "assigned_at", "created_at")
    list_filter = ("status",)


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "annotator", "submitted_at")
