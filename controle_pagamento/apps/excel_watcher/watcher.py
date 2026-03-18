import logging
import os
import threading
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

_observer = None
_debounce_timer = None
_lock = threading.Lock()


def _importar_em_thread(caminho_arquivo):
    def executar():
        time.sleep(2)
        logger.info(f"🔄 Arquivo modificado, reimportando: {caminho_arquivo}")
        try:
            from apps.excel_watcher.excel_processor import processar_excel
            result = processar_excel(caminho_arquivo)
            if result['sucesso']:
                from apps.excel_watcher.consumers import notify_dashboard_update
                notify_dashboard_update(result)
                logger.info(f"✅ Reimportação concluída: {result['registros']} registros")
            else:
                logger.error(f"❌ Reimportação falhou: {result['mensagem']}")
        except Exception as e:
            logger.error(f"❌ Erro na reimportação: {e}", exc_info=True)

    t = threading.Thread(target=executar, daemon=True)
    t.start()


class ExcelFileHandler(FileSystemEventHandler):
    def __init__(self, caminho_arquivo):
        self.caminho_arquivo = os.path.normpath(caminho_arquivo)
        super().__init__()

    def on_modified(self, event):
        if event.is_directory:
            return

        caminho_evento = os.path.normpath(event.src_path)
        nome_arquivo = os.path.basename(caminho_evento)

        if not (nome_arquivo.endswith('.xlsm') or nome_arquivo.endswith('.xlsx')):
            return

        if self.caminho_arquivo and caminho_evento != self.caminho_arquivo:
            return

        logger.info(f"📁 Mudança detectada: {caminho_evento}")
        self._debounce(caminho_evento)

    def _debounce(self, caminho):
        global _debounce_timer
        with _lock:
            if _debounce_timer:
                _debounce_timer.cancel()
            _debounce_timer = threading.Timer(3.0, _importar_em_thread, args=[caminho])
            _debounce_timer.daemon = True
            _debounce_timer.start()


def start_watcher():
    global _observer
    from django.conf import settings

    watch_dir = getattr(settings, 'EXCEL_WATCH_DIR', '')
    excel_path = getattr(settings, 'EXCEL_FILE_PATH', '')

    if not watch_dir:
        logger.warning("⚠️  EXCEL_WATCH_DIR não configurado. Watcher não iniciado.")
        return

    if not os.path.isdir(watch_dir):
        logger.warning(f"⚠️  Diretório não encontrado: {watch_dir}. Watcher não iniciado.")
        return

    if _observer and _observer.is_alive():
        logger.info("ℹ️  Watcher já está em execução.")
        return

    handler = ExcelFileHandler(excel_path)
    _observer = Observer()
    _observer.schedule(handler, path=watch_dir, recursive=False)
    _observer.daemon = True
    _observer.start()
    logger.info(f"👀 Watcher iniciado, monitorando: {watch_dir}")


def stop_watcher():
    global _observer
    if _observer and _observer.is_alive():
        _observer.stop()
        _observer.join()
        logger.info("🛑 Watcher parado.")
