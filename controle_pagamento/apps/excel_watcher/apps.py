import logging
import os
import threading

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ExcelWatcherConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.excel_watcher'
    verbose_name = 'Excel Watcher'

    def ready(self):
        if os.environ.get('RUN_MAIN') != 'true':
            return

        from django.conf import settings
        excel_path = getattr(settings, 'EXCEL_FILE_PATH', '')
        watch_dir = getattr(settings, 'EXCEL_WATCH_DIR', '')

        if not excel_path or not watch_dir:
            logger.warning(
                '⚠️  EXCEL_FILE_PATH e EXCEL_WATCH_DIR não configurados no .env. '
                'O monitoramento automático está desativado.'
            )
        else:
            from apps.excel_watcher.watcher import start_watcher
            start_watcher()

            def importar_inicial():
                try:
                    from apps.excel_watcher.excel_processor import processar_excel
                    result = processar_excel(excel_path)
                    logger.info(f"✅ Importação inicial concluída: {result}")
                except Exception as e:
                    logger.warning(f"⚠️  Importação inicial falhou: {e}")

            t = threading.Thread(target=importar_inicial, daemon=True)
            t.start()
