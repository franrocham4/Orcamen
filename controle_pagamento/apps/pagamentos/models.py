from django.db import models


class Pagamento(models.Model):
    nome = models.CharField(max_length=255, blank=True, null=True)
    descricao = models.CharField(max_length=500, blank=True, null=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)

    valor = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    valor_pago = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    valor_pendente = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    data_vencimento = models.DateField(null=True, blank=True)
    data_pagamento = models.DateField(null=True, blank=True)
    mes_referencia = models.CharField(max_length=20, blank=True, null=True)
    competencia = models.CharField(max_length=20, blank=True, null=True)

    STATUS_CHOICES = [
        ('pago', 'Pago'),
        ('pendente', 'Pendente'),
        ('atrasado', 'Atrasado'),
        ('cancelado', 'Cancelado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')

    observacoes = models.TextField(blank=True, null=True)
    categoria = models.CharField(max_length=100, blank=True, null=True)
    responsavel = models.CharField(max_length=255, blank=True, null=True)
    fornecedor = models.CharField(max_length=255, blank=True, null=True)
    numero_nf = models.CharField(max_length=100, blank=True, null=True)
    banco = models.CharField(max_length=100, blank=True, null=True)
    forma_pagamento = models.CharField(max_length=100, blank=True, null=True)

    dados_extras = models.JSONField(default=dict, blank=True)

    linha_planilha = models.IntegerField(null=True, blank=True)
    aba_planilha = models.CharField(max_length=100, default='Sheet1')

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.nome or 'Sem nome'} - {self.valor or 0} ({self.status})"


class ImportacaoExcel(models.Model):
    arquivo_nome = models.CharField(max_length=255)
    data_importacao = models.DateTimeField(auto_now_add=True)
    registros_importados = models.IntegerField(default=0)
    sucesso = models.BooleanField(default=True)
    mensagem = models.TextField(blank=True)
    abas_processadas = models.JSONField(default=list)

    class Meta:
        verbose_name = 'Importação Excel'
        verbose_name_plural = 'Importações Excel'
        ordering = ['-data_importacao']

    def __str__(self):
        status = '✅' if self.sucesso else '❌'
        return f"{status} {self.arquivo_nome} - {self.data_importacao.strftime('%d/%m/%Y %H:%M')}"
