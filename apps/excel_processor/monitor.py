"""
MonitorPasta: watches a local folder for Excel file changes using watchdog.
When a change is detected, triggers a Celery task (or inline processing if Celery is unavailable).
"""
import logging
import os
import threading
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

EXCEL_EXTENSIONS = ('.xlsx', '.xlsm', '.xls')

_observer = None
_observer_lock = threading.Lock()


class ExcelFileHandler(FileSystemEventHandler):
    """Handles file system events for Excel files."""

    def __init__(self, debounce_seconds: float = 3.0):
        super().__init__()
        self._pending = {}
        self._debounce = debounce_seconds
        self._lock = threading.Lock()

    def _is_excel(self, path: str) -> bool:
        name = os.path.basename(path)
        return (
            any(name.lower().endswith(ext) for ext in EXCEL_EXTENSIONS)
            and not name.startswith('~$')
        )

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
        logger.info(f'Detected change in Excel file: {filepath}')
        try:
            from .tasks import processar_excel_task
            processar_excel_task.delay(filepath, trigger='watchdog')
            logger.info(f'Queued Celery task for: {filepath}')
        except Exception:
            # Celery/Redis not available — process inline
            logger.warning('Celery unavailable, processing inline...')
            try:
                from .processors import ProcessadorExcel
                ProcessadorExcel(filepath).processar()
            except Exception as e:
                logger.error(f'Inline processing failed: {e}')

    def on_created(self, event):
        if not event.is_directory and self._is_excel(event.src_path):
            self._schedule(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._is_excel(event.src_path):
            self._schedule(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and self._is_excel(event.dest_path):
            self._schedule(event.dest_path)


def iniciar_monitoramento(folder: str = None):
    """Start the folder watcher. Call once at startup."""
    global _observer

    with _observer_lock:
        if _observer is not None and _observer.is_alive():
            return  # Already running

        if folder is None:
            from django.conf import settings
            folder = getattr(settings, 'WATCH_FOLDER', os.getcwd())

        if not os.path.isdir(folder):
            logger.warning(f'Watch folder does not exist (yet): {folder}')
            # Don't crash — maybe the folder will be created later
            return

        handler = ExcelFileHandler(debounce_seconds=2.0)
        _observer = Observer()
        _observer.schedule(handler, folder, recursive=False)
        _observer.daemon = True
        _observer.start()
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
