import json
import logging

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

logger = logging.getLogger(__name__)

GROUP_NAME = 'dashboard_updates'


class DashboardConsumer(WebsocketConsumer):
    def connect(self):
        async_to_sync(self.channel_layer.group_add)(
            GROUP_NAME,
            self.channel_name,
        )
        self.accept()
        logger.info(f"🟢 WebSocket conectado: {self.channel_name}")

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            GROUP_NAME,
            self.channel_name,
        )
        logger.info(f"🔴 WebSocket desconectado: {self.channel_name}")

    def receive(self, text_data):
        try:
            data = json.loads(text_data)
            logger.debug(f"📨 Mensagem recebida: {data}")
        except json.JSONDecodeError:
            pass

    def dashboard_update(self, event):
        self.send(text_data=json.dumps({
            'type': 'excel_updated',
            'data': event.get('data', {}),
        }))


def notify_dashboard_update(result):
    try:
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning("⚠️  Channel layer não disponível.")
            return

        async_to_sync(channel_layer.group_send)(
            GROUP_NAME,
            {
                'type': 'dashboard_update',
                'data': {
                    'registros': result.get('registros', 0),
                    'mensagem': result.get('mensagem', ''),
                    'abas': result.get('abas', []),
                },
            }
        )
        logger.info("📡 Notificação WebSocket enviada para todos os clientes.")
    except Exception as e:
        logger.error(f"❌ Erro ao notificar WebSocket: {e}", exc_info=True)
