import os
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import ExcelFile, ExcelSheet, ExcelRow, SyncHistory
from .serializers import (ExcelFileSerializer, ExcelSheetSerializer,
                           ExcelRowSerializer, SyncHistorySerializer)


class ExcelFileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExcelFile.objects.filter(is_active=True)
    serializer_class = ExcelFileSerializer

    @action(detail=True, methods=['post'])
    def sincronizar(self, request, pk=None):
        """Trigger synchronization for a specific file."""
        excel_file = self.get_object()
        try:
            from .tasks import processar_excel_task
            processar_excel_task.delay(excel_file.filepath, trigger='manual_api')
            return Response({'message': 'Sincronização iniciada', 'file': excel_file.filename})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExcelSheetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExcelSheet.objects.select_related('excel_file').all()
    serializer_class = ExcelSheetSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        file_id = self.request.query_params.get('file')
        if file_id:
            qs = qs.filter(excel_file_id=file_id)
        return qs


class ExcelRowViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExcelRow.objects.select_related('sheet').all()
    serializer_class = ExcelRowSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        sheet_id = self.request.query_params.get('sheet')
        if sheet_id:
            qs = qs.filter(sheet_id=sheet_id)
        search = self.request.query_params.get('search')
        if search:
            # Filter rows where any value contains the search term
            from django.db.models import Q
            qs = qs.filter(data__icontains=search)
        return qs


class SyncHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SyncHistory.objects.select_related('excel_file').all()
    serializer_class = SyncHistorySerializer

    @action(detail=False, methods=['post'])
    def sincronizar_agora(self, request):
        """Trigger manual synchronization of the configured Excel file."""
        watch_folder = getattr(settings, 'WATCH_FOLDER', os.getcwd())
        excel_filename = getattr(settings, 'EXCEL_FILENAME', '')

        filepath = os.path.join(watch_folder, excel_filename) if excel_filename else None

        # If the configured path doesn't exist, try the repo root
        if not filepath or not os.path.exists(filepath):
            repo_path = os.path.join(settings.BASE_DIR, excel_filename)
            if os.path.exists(repo_path):
                filepath = repo_path

        if not filepath or not os.path.exists(filepath):
            return Response(
                {'error': f'Arquivo não encontrado: {filepath}'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            from .tasks import processar_excel_task
            processar_excel_task.delay(filepath, trigger='manual_api')
            return Response({'message': 'Sincronização iniciada', 'filepath': filepath})
        except Exception:
            # Celery not available — process inline
            from .processors import ProcessadorExcel
            result = ProcessadorExcel(filepath).processar()
            return Response({'message': 'Sincronização concluída (inline)', 'result': result})
