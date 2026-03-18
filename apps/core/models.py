from django.db import models
import json


class ExcelFile(models.Model):
    """Represents an Excel file that was processed."""
    filename = models.CharField(max_length=255, verbose_name='Nome do Arquivo')
    filepath = models.CharField(max_length=1000, verbose_name='Caminho')
    file_size = models.BigIntegerField(default=0, verbose_name='Tamanho (bytes)')
    last_modified = models.DateTimeField(null=True, blank=True, verbose_name='Última Modificação do Arquivo')
    processed_at = models.DateTimeField(auto_now=True, verbose_name='Processado em')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    is_active = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Arquivo Excel'
        verbose_name_plural = 'Arquivos Excel'
        ordering = ['-processed_at']

    def __str__(self):
        return self.filename


class ExcelSheet(models.Model):
    """Represents a sheet (aba) within an Excel file."""
    excel_file = models.ForeignKey(
        ExcelFile, on_delete=models.CASCADE,
        related_name='sheets', verbose_name='Arquivo Excel'
    )
    name = models.CharField(max_length=255, verbose_name='Nome da Aba')
    sheet_index = models.IntegerField(default=0, verbose_name='Índice')
    row_count = models.IntegerField(default=0, verbose_name='Total de Linhas')
    col_count = models.IntegerField(default=0, verbose_name='Total de Colunas')
    headers = models.JSONField(default=list, verbose_name='Cabeçalhos')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Aba da Planilha'
        verbose_name_plural = 'Abas da Planilha'
        ordering = ['sheet_index']
        unique_together = ['excel_file', 'name']

    def __str__(self):
        return f'{self.excel_file.filename} - {self.name}'


class ExcelRow(models.Model):
    """Represents a single data row in a sheet."""
    sheet = models.ForeignKey(
        ExcelSheet, on_delete=models.CASCADE,
        related_name='rows', verbose_name='Aba'
    )
    row_number = models.IntegerField(verbose_name='Número da Linha')
    data = models.JSONField(default=dict, verbose_name='Dados')

    class Meta:
        verbose_name = 'Linha da Planilha'
        verbose_name_plural = 'Linhas da Planilha'
        ordering = ['row_number']
        unique_together = ['sheet', 'row_number']

    def __str__(self):
        return f'{self.sheet.name} - Linha {self.row_number}'


class SyncHistory(models.Model):
    """Tracks synchronization history."""

    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('running', 'Processando'),
        ('success', 'Sucesso'),
        ('error', 'Erro'),
    ]

    excel_file = models.ForeignKey(
        ExcelFile, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sync_history', verbose_name='Arquivo Excel'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Status')
    trigger = models.CharField(max_length=50, default='manual', verbose_name='Gatilho')
    sheets_processed = models.IntegerField(default=0, verbose_name='Abas Processadas')
    rows_processed = models.IntegerField(default=0, verbose_name='Linhas Processadas')
    error_message = models.TextField(blank=True, verbose_name='Mensagem de Erro')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Iniciado em')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Finalizado em')
    duration_seconds = models.FloatField(null=True, blank=True, verbose_name='Duração (seg)')

    class Meta:
        verbose_name = 'Histórico de Sincronização'
        verbose_name_plural = 'Histórico de Sincronizações'
        ordering = ['-started_at']

    def __str__(self):
        return f'Sync {self.id} - {self.status} em {self.started_at}'
