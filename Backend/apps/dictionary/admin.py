from django.contrib import admin
from .models import Dictionary


@admin.register(Dictionary)
class DictionaryAdmin(admin.ModelAdmin):
    list_display   = ('id', 'word', 'word_length', 'difficulty', 'is_active')
    list_filter    = ('difficulty', 'is_active', 'word_length')
    search_fields  = ('word',)
    ordering       = ('word',)
    list_editable  = ('is_active', 'difficulty')   # toggle directly from list view