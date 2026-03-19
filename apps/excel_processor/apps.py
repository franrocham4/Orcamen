from django.apps import AppConfig
import os


class ExcelProcessorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.excel_processor'
    verbose_name = 'Processador Excel'

    def ready(self):
        """Start file watcher when Django is ready (only in main process)."""
        # RUN_MAIN=true is set by Django's auto-reloader for the child process.
        # START_WATCHER=true can be used to force the watcher in other contexts
        # (e.g. gunicorn). When neither is set we're likely inside a management
        # command (migrate, shell, …) and should not start the background thread.
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('START_WATCHER') == 'true':
            self._sync_folder_on_startup()
            try:
                from django.conf import settings
                from .monitor import iniciar_monitoramento
                folder_path = getattr(settings, 'EXCEL_FOLDER_PATH', getattr(settings, 'WATCH_FOLDER', ''))
                iniciar_monitoramento(folder_path or None)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f'Could not start file watcher: {e}')

    def _sync_folder_on_startup(self):
        """Remove ghost DB records before the folder monitor starts."""
        import logging
        logger = logging.getLogger(__name__)
        print('🔄 Sincronizando BD com pasta...')
        try:
            from django.core.management import call_command
            call_command('sync_excel_folder')
        except Exception as e:
            logger.warning(f'Could not run startup folder sync: {e}')
