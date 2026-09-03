from django.contrib import admin

from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ["subject", "reporter", "category", "status", "created_at"]
    list_filter = ["category", "status"]
    search_fields = ["subject", "description", "reporter__email"]
