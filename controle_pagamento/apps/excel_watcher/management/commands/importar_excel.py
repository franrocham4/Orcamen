import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Importa dados da planilha Excel para o banco de dados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--arquivo',
            type=str,
            help='Caminho alternativo para o arquivo Excel',
        )

    def handle(self, *args, **options):
        caminho = options.get('arquivo') or getattr(settings, 'EXCEL_FILE_PATH', '')

        if not caminho:
            self.stderr.write(self.style.ERROR(
                '❌ Caminho do arquivo não configurado. '
                'Configure EXCEL_FILE_PATH no .env ou use --arquivo'
            ))
            return

        self.stdout.write(self.style.WARNING(f'📊 Importando: {caminho}'))

        from apps.excel_watcher.excel_processor import processar_excel
        result = processar_excel(caminho)

        if result['sucesso']:
            self.stdout.write(self.style.SUCCESS(
                f"✅ {result['mensagem']}\n"
                f"   📁 Registros importados: {result['registros']}\n"
                f"   📋 Abas processadas: {', '.join(result.get('abas', []))}"
            ))
        else:
            self.stderr.write(self.style.ERROR(f"❌ {result['mensagem']}"))
