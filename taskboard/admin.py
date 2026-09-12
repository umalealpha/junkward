from django.contrib import admin

from .models import CompletionNote, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "task", "type", "acknowledged", "seen_at", "created_at")
    list_filter = ("type", "acknowledged")
    raw_id_fields = ("recipient", "task")


@admin.register(CompletionNote)
class CompletionNoteAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "interaction_seconds", "created_at")
    raw_id_fields = ("task", "author")
