from django.contrib import admin

from .models import Attempt, AttemptAnswer, AttemptStage


class StageInline(admin.TabularInline):
    model = AttemptStage
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in AttemptStage._meta.fields]


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "branch", "subject", "status", "total_score", "max_score",
                    "started_at", "finished_at")
    list_filter = ("status", "branch", "subject")
    search_fields = ("first_name", "last_name")
    readonly_fields = [f.name for f in Attempt._meta.fields if f.name != "retake_allowed"]
    exclude = ("token_hash", "identity_key")
    inlines = [StageInline]

    def has_add_permission(self, request):
        return False


@admin.register(AttemptAnswer)
class AttemptAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "stage", "position", "is_correct", "points_awarded")
    list_filter = ("stage", "is_correct")
    readonly_fields = [f.name for f in AttemptAnswer._meta.fields]

    def has_add_permission(self, request):
        return False
