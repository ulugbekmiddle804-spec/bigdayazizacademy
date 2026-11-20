from django.contrib import admin

from .models import Branch, Option, Question, StageConfig, Subject


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    search_fields = ("name", "address")


class StageInline(admin.TabularInline):
    model = StageConfig
    extra = 0


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("__str__", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    inlines = [StageInline]


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0
    min_num = 2


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("short_text", "subject", "stage", "difficulty", "points", "is_active")
    list_filter = ("subject", "stage", "difficulty", "is_active")
    search_fields = ("text",)
    inlines = [OptionInline]

    @admin.display(description="Savol")
    def short_text(self, obj):
        return obj.text[:90]
