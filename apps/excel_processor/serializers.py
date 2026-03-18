from rest_framework import serializers
from apps.core.models import ExcelFile, ExcelSheet, ExcelRow, SyncHistory


class ExcelFileSerializer(serializers.ModelSerializer):
    sheet_count = serializers.SerializerMethodField()

    class Meta:
        model = ExcelFile
        fields = ['id', 'filename', 'filepath', 'file_size', 'last_modified',
                  'processed_at', 'is_active', 'sheet_count']

    def get_sheet_count(self, obj):
        return obj.sheets.count()


class ExcelSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcelSheet
        fields = ['id', 'name', 'sheet_index', 'row_count', 'col_count',
                  'headers', 'updated_at', 'excel_file']


class ExcelRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExcelRow
        fields = ['id', 'row_number', 'data']


class SyncHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncHistory
        fields = ['id', 'status', 'trigger', 'sheets_processed', 'rows_processed',
                  'error_message', 'started_at', 'finished_at', 'duration_seconds',
                  'excel_file']
