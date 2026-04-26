from django.contrib import admin
from .models import Dictionary

@admin.register(Dictionary)
class DictionaryAdmin(admin.ModelAdmin):
    list_display = ("id", "word", "word_length", "difficulty", "is_active")
    search_fields = ('word',)
    list_filter = ("difficulty", "is_active")
