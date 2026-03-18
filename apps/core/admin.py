from django.contrib import admin
from .models import ExcelFile, ExcelSheet, ExcelRow, SyncHistory


@admin.register(ExcelFile)
class ExcelFileAdmin(admin.ModelAdmin):
    list_display = ['filename', 'file_size', 'last_modified', 'processed_at', 'is_active']
    list_filter = ['is_active']
    search_fields = ['filename', 'filepath']


@admin.register(ExcelSheet)
class ExcelSheetAdmin(admin.ModelAdmin):
    list_display = ['name', 'excel_file', 'row_count', 'col_count', 'updated_at']
    list_filter = ['excel_file']
    search_fields = ['name']


@admin.register(ExcelRow)
class ExcelRowAdmin(admin.ModelAdmin):
    list_display = ['sheet', 'row_number']
    list_filter = ['sheet']
    search_fields = ['sheet__name']


@admin.register(SyncHistory)
class SyncHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'trigger', 'sheets_processed', 'rows_processed', 'started_at', 'duration_seconds']
    list_filter = ['status', 'trigger']
    readonly_fields = ['started_at', 'finished_at', 'duration_seconds']
