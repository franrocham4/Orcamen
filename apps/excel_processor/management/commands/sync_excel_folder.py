"""
Management command: sync_excel_folder

Compares the Excel files actually present in the configured watch folder against the
database records and removes any "ghost" entries (DB records whose file no longer
exists on disk).  Also prints the files that were found so the operator can confirm
the folder contents.

Usage:
    python manage.py sync_excel_folder
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand

EXCEL_EXTENSIONS = ('.xlsx', '.xlsm', '.xls')


class Command(BaseCommand):
    help = 'Sincroniza BD com arquivos reais na pasta — remove planilhas fantasmas'

    def handle(self, *args, **options):
        from apps.core.models import ExcelFile

        folder_path = getattr(
            settings,
            'EXCEL_FOLDER_PATH',
            getattr(settings, 'WATCH_FOLDER', str(settings.BASE_DIR)),
        )

        self.stdout.write(f'📁 Verificando pasta: {folder_path}')

        # Collect real Excel files present on disk
        real_filenames: set[str] = set()
        if os.path.isdir(folder_path):
            for fname in os.listdir(folder_path):
                if (
                    fname.lower().endswith(EXCEL_EXTENSIONS)
                    and not fname.startswith('~$')
                ):
                    real_filenames.add(fname)
                    self.stdout.write(f'✅ Encontrado: {fname}')
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Pasta não encontrada: {folder_path}')
            )

        # Remove DB records whose file is no longer on disk (check by full path)
        deleted_count = 0
        for excel_file in ExcelFile.objects.all():
            # Primary check: does the stored filepath actually exist on disk?
            # If the filepath points outside the configured folder (e.g., old data),
            # also check by filename within the current folder as a fallback.
            file_on_disk = os.path.exists(excel_file.filepath) or (
                excel_file.filename in real_filenames
            )
            if not file_on_disk:
                self.stdout.write(
                    self.style.WARNING(f'🗑️  Deletando fantasma: {excel_file.filename}')
                )
                excel_file.delete()  # cascades to ExcelSheet and ExcelRow
                deleted_count += 1

        if deleted_count:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Sincronização de pasta completa! {deleted_count} fantasma(s) removido(s).'
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS('✅ Sincronização de pasta completa! Nenhum fantasma encontrado.'))
