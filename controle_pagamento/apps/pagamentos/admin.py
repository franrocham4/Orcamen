from django.contrib import admin
from .models import Pagamento, ImportacaoExcel


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'valor', 'status', 'data_vencimento', 'mes_referencia', 'categoria')
    list_filter = ('status', 'mes_referencia', 'categoria', 'aba_planilha')
    search_fields = ('nome', 'fornecedor', 'descricao', 'referencia', 'numero_nf')
    readonly_fields = ('criado_em', 'atualizado_em')


@admin.register(ImportacaoExcel)
class ImportacaoExcelAdmin(admin.ModelAdmin):
    list_display = ('arquivo_nome', 'data_importacao', 'registros_importados', 'sucesso')
    list_filter = ('sucesso',)
    readonly_fields = ('data_importacao',)
