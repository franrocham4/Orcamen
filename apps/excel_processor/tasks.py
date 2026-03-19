"""
Celery tasks for Excel processing.
"""
import logging
from datetime import datetime, timezone

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def processar_excel_task(self, filepath: str, trigger: str = 'auto'):
    """
    Celery task: Process an Excel file and update the database.
    """
    from apps.core.models import SyncHistory
    from .processors import ProcessadorExcel

    sync = SyncHistory.objects.create(
        status='running',
        trigger=trigger,
    )

    started = datetime.now(tz=timezone.utc)

    try:
        processor = ProcessadorExcel(filepath)
        result = processor.processar(sync_history=sync)

        elapsed = (datetime.now(tz=timezone.utc) - started).total_seconds()

        if result.get('success'):
            sync.status = 'success'
            sync.sheets_processed = result.get('sheets', 0)
            sync.rows_processed = result.get('rows', 0)
        else:
            sync.status = 'error'
            sync.error_message = result.get('error', 'Unknown error')

        sync.finished_at = datetime.now(tz=timezone.utc)
        sync.duration_seconds = elapsed
        sync.save()

        logger.info(f'Task completed: {result}')
        return result

    except Exception as exc:
        elapsed = (datetime.now(tz=timezone.utc) - started).total_seconds()
        sync.status = 'error'
        sync.error_message = str(exc)
        sync.finished_at = datetime.now(tz=timezone.utc)
        sync.duration_seconds = elapsed
        sync.save()

        logger.error(f'Task failed: {exc}')
        raise self.retry(exc=exc)


@shared_task
def desativar_arquivo_task(filepath: str):
    """
    Celery task: Deactivate an ExcelFile record when the file is deleted from disk.
    """
    from .processors import desativar_arquivo
    desativar_arquivo(filepath)
    return {'deactivated': filepath}


@shared_task
def sincronizar_pasta_task(folder_path: str):
    """
    Process all Excel files found in a folder.
    """
    import os
    excel_extensions = ('.xlsx', '.xlsm', '.xls')
    found = []
    for fname in os.listdir(folder_path):
        if fname.lower().endswith(excel_extensions) and not fname.startswith('~$'):
            full_path = os.path.join(folder_path, fname)
            processar_excel_task.delay(full_path, trigger='folder_scan')
            found.append(fname)
    return {'files_queued': found}
