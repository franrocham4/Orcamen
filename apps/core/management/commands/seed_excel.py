"""
Management command: seed_excel
Reads the Excel file included in the repository and seeds the database.
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Seeds the database from the Excel file in the repository.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', type=str, default=None,
            help='Path to Excel file (defaults to EXCEL_FILENAME in repo root or WATCH_FOLDER)'
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Re-process even if already seeded'
        )

    def handle(self, *args, **options):
        from apps.core.models import ExcelFile
        from apps.excel_processor.processors import ProcessadorExcel

        filepath = options.get('file')

        if not filepath:
            excel_filename = getattr(settings, 'EXCEL_FILENAME', 'CONTROLE DE PAGAMENTO 2025.xlsm')

            # Try repo root first
            candidates = [
                os.path.join(settings.BASE_DIR, excel_filename),
                os.path.join(getattr(settings, 'WATCH_FOLDER', ''), excel_filename),
            ]
            for path in candidates:
                if os.path.exists(path):
                    filepath = path
                    break

        if not filepath or not os.path.exists(filepath):
            self.stderr.write(self.style.ERROR(f'Excel file not found. Tried: {candidates}'))
            return

        if not options['force']:
            existing = ExcelFile.objects.filter(filepath=filepath).first()
            if existing:
                self.stdout.write(self.style.WARNING(
                    f'File already seeded: {filepath}. Use --force to re-process.'
                ))
                return

        self.stdout.write(f'Processing: {filepath}')
        processor = ProcessadorExcel(filepath)
        result = processor.processar()

        if result.get('success'):
            self.stdout.write(self.style.SUCCESS(
                f'Done! {result["sheets"]} sheets, {result["rows"]} rows imported.'
            ))
        else:
            self.stderr.write(self.style.ERROR(f'Failed: {result.get("error")}'))
