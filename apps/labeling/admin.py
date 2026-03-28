from django.contrib import admin

from apps.labeling.models import Annotation, Task, TaskAssignment


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "status", "current_round", "validation_score", "created_at")
    list_filter = ("status",)


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "annotator", "round_number", "status", "assigned_at", "submitted_at")
    list_filter = ("status", "round_number")


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "annotator", "assignment", "submitted_at")
