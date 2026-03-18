import os
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.utils import timezone
from django.conf import settings
from django.db.models import Count, Sum

from apps.core.models import ExcelFile, ExcelSheet, ExcelRow, SyncHistory


class IndexView(View):
    """Landing page — redirects to dashboard."""
    def get(self, request):
        from django.shortcuts import redirect
        return redirect('dashboard:dashboard')


class DashboardView(View):
    """Main dashboard showing overview of all data."""
    def get(self, request):
        files = ExcelFile.objects.filter(is_active=True).prefetch_related('sheets')
        recent_syncs = SyncHistory.objects.select_related('excel_file').order_by('-started_at')[:10]
        last_sync = SyncHistory.objects.filter(status='success').order_by('-started_at').first()

        total_files = files.count()
        total_sheets = ExcelSheet.objects.count()
        total_rows = ExcelRow.objects.count()
        error_syncs = SyncHistory.objects.filter(status='error').count()

        context = {
            'files': files,
            'recent_syncs': recent_syncs,
            'last_sync': last_sync,
            'total_files': total_files,
            'total_sheets': total_sheets,
            'total_rows': total_rows,
            'error_syncs': error_syncs,
            'watch_folder': getattr(settings, 'WATCH_FOLDER', ''),
            'excel_filename': getattr(settings, 'EXCEL_FILENAME', ''),
        }
        return render(request, 'dashboard/dashboard.html', context)


class SheetsListView(View):
    """Lists all sheets from all files."""
    def get(self, request):
        file_id = request.GET.get('file')
        if file_id:
            excel_file = get_object_or_404(ExcelFile, id=file_id)
            sheets = excel_file.sheets.order_by('sheet_index')
        else:
            sheets = ExcelSheet.objects.select_related('excel_file').order_by('excel_file', 'sheet_index')
            excel_file = None

        files = ExcelFile.objects.filter(is_active=True)
        context = {'sheets': sheets, 'files': files, 'selected_file': excel_file}
        return render(request, 'dashboard/sheets_list.html', context)


class SheetDetailView(View):
    """Shows all rows of a sheet with filtering and pagination."""
    def get(self, request, sheet_id):
        sheet = get_object_or_404(ExcelSheet, id=sheet_id)
        search = request.GET.get('search', '').strip()
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 50))

        rows_qs = sheet.rows.all()
        if search:
            rows_qs = rows_qs.filter(data__icontains=search)

        total_rows = rows_qs.count()
        total_pages = max(1, (total_rows + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page

        rows = rows_qs[offset:offset + per_page]

        # Build table-friendly list
        table_rows = [r.data for r in rows]

        context = {
            'sheet': sheet,
            'headers': sheet.headers,
            'table_rows': table_rows,
            'search': search,
            'page': page,
            'per_page': per_page,
            'total_rows': total_rows,
            'total_pages': total_pages,
            'pages': range(max(1, page - 2), min(total_pages + 1, page + 3)),
        }
        return render(request, 'dashboard/sheet_detail.html', context)


class SincronizarView(View):
    """Trigger manual synchronization."""
    def post(self, request):
        watch_folder = getattr(settings, 'WATCH_FOLDER', os.getcwd())
        excel_filename = getattr(settings, 'EXCEL_FILENAME', '')

        filepath = os.path.join(watch_folder, excel_filename) if excel_filename else None

        if not filepath or not os.path.exists(filepath):
            repo_path = os.path.join(settings.BASE_DIR, excel_filename)
            if os.path.exists(repo_path):
                filepath = repo_path

        if not filepath or not os.path.exists(filepath):
            return JsonResponse({'error': f'Arquivo não encontrado'}, status=404)

        try:
            from apps.excel_processor.tasks import processar_excel_task
            processar_excel_task.delay(filepath, trigger='manual_dashboard')
            return JsonResponse({'message': 'Sincronização iniciada em background'})
        except Exception:
            # Inline if Celery not available
            from apps.excel_processor.processors import ProcessadorExcel
            result = ProcessadorExcel(filepath).processar()
            return JsonResponse({'message': 'Sincronização concluída', 'result': result})


class SyncStatusView(View):
    """Returns latest sync status as JSON (for polling)."""
    def get(self, request):
        last = SyncHistory.objects.order_by('-started_at').first()
        if not last:
            return JsonResponse({'status': 'none'})
        return JsonResponse({
            'id': last.id,
            'status': last.status,
            'trigger': last.trigger,
            'started_at': last.started_at.isoformat(),
            'finished_at': last.finished_at.isoformat() if last.finished_at else None,
            'sheets_processed': last.sheets_processed,
            'rows_processed': last.rows_processed,
            'error_message': last.error_message,
        })
