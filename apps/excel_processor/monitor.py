"""
MonitorPasta: watches a local folder for Excel file changes using watchdog.
When a change is detected, triggers a Celery task (or inline processing if Celery is unavailable).
"""
import logging
import os
import threading
import time
import zipfile

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

EXCEL_EXTENSIONS = ('.xlsx', '.xlsm', '.xls')
TEMP_EXCEL_PREFIX = '~$'

_observer = None
_observer_lock = threading.Lock()


class ExcelFileHandler(FileSystemEventHandler):
    """Handles file system events for Excel files."""

    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1.0
    FILE_CLOSE_DELAY = 2.0

    def __init__(self, debounce_seconds: float = 3.0):
        super().__init__()
        self._pending = {}
        self._debounce = debounce_seconds
        self._lock = threading.Lock()

    def _is_excel(self, path: str) -> bool:
        name = os.path.basename(path)
        if not any(name.lower().endswith(ext) for ext in EXCEL_EXTENSIONS):
            return False
        if name.startswith(TEMP_EXCEL_PREFIX):
            print(f'⏭️ Ignorando arquivo temporário: {name}')
            return False
        return True

    def _is_file_locked(self, filepath: str) -> bool:
        """Check if a file is currently locked/in use."""
        try:
            with open(filepath, 'rb'):
                return False
        except (IOError, OSError):
            return True

    def _wait_for_file_ready(self, filepath: str) -> bool:
        """Wait for a file to be ready for reading. Returns True if ready, False on timeout."""
        for attempt in range(self.RETRY_ATTEMPTS):
            if not self._is_file_locked(filepath):
                # Extra pause to ensure the file is fully written before reading
                time.sleep(self.FILE_CLOSE_DELAY)
                return True
            if attempt < self.RETRY_ATTEMPTS - 1:
                print(f'⏳ Arquivo ainda em uso, aguardando... ({attempt + 1}/{self.RETRY_ATTEMPTS})')
                time.sleep(self.RETRY_DELAY)
        return False

    def _schedule(self, filepath: str):
        """Debounce: wait a bit before processing to avoid double events."""
        with self._lock:
            self._pending[filepath] = time.monotonic() + self._debounce

        def check_and_fire():
            time.sleep(self._debounce + 0.5)
            with self._lock:
                due = self._pending.get(filepath)
                if due is None or time.monotonic() < due:
                    return
                del self._pending[filepath]
            self._dispatch(filepath)

        threading.Thread(target=check_and_fire, daemon=True).start()

    def _dispatch(self, filepath: str):
        filename = os.path.basename(filepath)
        logger.info(f'Detected change in Excel file: {filepath}')

        if not os.path.exists(filepath):
            logger.warning(f'File no longer exists, skipping: {filepath}')
            return

        if not self._wait_for_file_ready(filepath):
            print(f'❌ Timeout: Arquivo ainda está em uso: {filepath}')
            logger.error(f'Timeout waiting for file to be ready: {filepath}')
            return

        try:
            from .tasks import processar_excel_task
            processar_excel_task.delay(filepath, trigger='watchdog')
            logger.info(f'Queued Celery task for: {filepath}')
        except Exception:
            # Celery/Redis not available — process inline with retry
            logger.warning('Celery unavailable, processing inline...')
            for attempt in range(self.RETRY_ATTEMPTS):
                try:
                    from .processors import ProcessadorExcel
                    ProcessadorExcel(filepath).processar()
                    print(f'✅ {filename} sincronizado com sucesso')
                    return
                except Exception as e:
                    is_file_error = (
                        (isinstance(e, ValueError) and 'closed file' in str(e))
                        or isinstance(e, zipfile.BadZipFile)
                    )
                    if is_file_error and attempt < self.RETRY_ATTEMPTS - 1:
                        print(f'⚠️ Erro ao ler arquivo, tentando novamente ({attempt + 1}/{self.RETRY_ATTEMPTS})')
                        time.sleep(self.RETRY_DELAY)
                    else:
                        logger.error(f'Inline processing failed: {e}')
                        print(f'❌ Erro ao processar {filename}: {e}')
                        return

    def _dispatch_deleted(self, filepath: str):
        """Handle deletion of an Excel file from the watched folder."""
        filename = os.path.basename(filepath)
        logger.info(f'Detected deletion of Excel file: {filepath}')
        # Always remove the record from the database immediately (do not rely solely on
        # Celery, because the worker may not be running even when Redis/Celery is configured).
        try:
            from .processors import desativar_arquivo
            desativar_arquivo(filepath)
            print(f'✅ {filename} removido do sistema')
        except Exception as e:
            logger.error(f'Inline deletion failed: {e}')
            print(f'❌ Erro ao remover {filename}: {e}')
        # Additionally queue a Celery task so distributed workers stay in sync.
        try:
            from .tasks import desativar_arquivo_task
            desativar_arquivo_task.delay(filepath)
            logger.info(f'Queued deletion task for: {filepath}')
        except Exception:
            pass  # Celery not available — inline deletion above already handled it

    def on_created(self, event):
        if not event.is_directory and self._is_excel(event.src_path):
            print(f'📥 Planilha ADICIONADA: {event.src_path}')
            self._schedule(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._is_excel(event.src_path):
            print(f'✏️  Planilha MODIFICADA: {event.src_path}')
            self._schedule(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self._is_excel(event.src_path):
            print(f'🗑️  Planilha REMOVIDA: {event.src_path}')
            self._dispatch_deleted(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            old_is_excel = self._is_excel(event.src_path)
            new_is_excel = self._is_excel(event.dest_path)

            if old_is_excel and not new_is_excel:
                # Renamed to a non-Excel extension — treat as deletion
                self._dispatch_deleted(event.src_path)
            elif old_is_excel and new_is_excel:
                # Renamed to another Excel filename — deactivate old, process new
                self._dispatch_deleted(event.src_path)
                self._schedule(event.dest_path)
            elif new_is_excel:
                # Non-Excel renamed to Excel — treat as addition
                self._schedule(event.dest_path)


def _sincronizar_pasta_no_inicio(folder: str):
    """
    On startup: reconcile the database with the actual folder contents.
    - Files on disk but not in DB → process them.
    - Files in DB (active) but not on disk → deactivate them.
    """
    import django
    # Guard: only run when Django ORM is ready
    if not django.apps.registry.apps.models_ready:
        logger.warning('Startup folder sync skipped: Django models are not ready yet.')
        return

    try:
        from apps.core.models import ExcelFile
        from .processors import ProcessadorExcel, desativar_arquivo

        # Collect Excel files currently on disk
        disk_files = {}
        try:
            for fname in os.listdir(folder):
                if (
                    any(fname.lower().endswith(ext) for ext in EXCEL_EXTENSIONS)
                    and not fname.startswith('~$')
                ):
                    full_path = os.path.join(folder, fname)
                    disk_files[full_path] = fname
        except OSError as e:
            logger.warning(f'Could not list folder {folder}: {e}')
            return

        # Deactivate DB records whose file no longer exists on disk
        all_files = ExcelFile.objects.all()
        for excel_file in all_files:
            if excel_file.filepath not in disk_files:
                logger.info(f'Startup: file no longer on disk, deleting: {excel_file.filepath}')
                desativar_arquivo(excel_file.filepath)

        # Process files on disk that are new, inactive, or modified since last sync
        from datetime import datetime, timezone as dt_timezone
        for full_path in disk_files:
            excel_file = ExcelFile.objects.filter(filepath=full_path).first()
            needs_processing = False
            if not excel_file:
                logger.info(f'Startup: new file found on disk, processing: {full_path}')
                needs_processing = True
            else:
                try:
                    file_mtime = datetime.fromtimestamp(
                        os.stat(full_path).st_mtime, tz=dt_timezone.utc
                    )
                    if file_mtime > excel_file.processed_at:
                        logger.info(
                            f'Startup: file modified since last sync, reprocessing: {full_path}'
                        )
                        needs_processing = True
                except OSError:
                    pass

            if needs_processing:
                try:
                    ProcessadorExcel(full_path).processar()
                except Exception as e:
                    logger.error(f'Startup processing failed for {full_path}: {e}')

    except Exception as e:
        logger.error(f'Startup folder sync failed: {e}')


def iniciar_monitoramento(folder: str = None):
    """Start the folder watcher. Call once at startup."""
    global _observer

    with _observer_lock:
        if _observer is not None and _observer.is_alive():
            return  # Already running

        if folder is None:
            from django.conf import settings
            folder = getattr(settings, 'EXCEL_FOLDER_PATH', getattr(settings, 'WATCH_FOLDER', os.getcwd()))

        if not os.path.isdir(folder):
            logger.warning(f'Watch folder does not exist (yet): {folder}')
            # Don't crash — maybe the folder will be created later
            return

        # Reconcile DB with current folder contents before starting the watcher
        threading.Thread(target=_sincronizar_pasta_no_inicio, args=(folder,), daemon=True).start()

        handler = ExcelFileHandler(debounce_seconds=2.0)
        _observer = Observer()
        _observer.schedule(handler, folder, recursive=False)
        _observer.daemon = True
        _observer.start()
        print(f'🟢 Monitorando: {folder}')
        logger.info(f'File watcher started on: {folder}')


def parar_monitoramento():
    """Stop the folder watcher."""
    global _observer
    with _observer_lock:
        if _observer and _observer.is_alive():
            _observer.stop()
            _observer.join()
            _observer = None
            logger.info('File watcher stopped.')
