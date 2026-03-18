from django.apps import AppConfig


class ExcelProcessorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.excel_processor'
    verbose_name = 'Processador Excel'

    def ready(self):
        """Start file watcher when Django is ready (only in main process)."""
        import os
        # Only start watcher in runserver/gunicorn, not in migrations/management commands
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('START_WATCHER') == 'true':
            try:
                from .monitor import iniciar_monitoramento
                iniciar_monitoramento()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f'Could not start file watcher: {e}')
