import logging
from decimal import Decimal
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q

from apps.pagamentos.models import Pagamento, ImportacaoExcel

logger = logging.getLogger(__name__)


def _calcular_kpis():
    pagamentos = Pagamento.objects.all()

    total_registros = pagamentos.count()
    total_valor = pagamentos.aggregate(total=Sum('valor'))['total'] or Decimal('0')
    total_pago = pagamentos.filter(status='pago').aggregate(total=Sum('valor'))['total'] or Decimal('0')
    total_pendente = pagamentos.filter(
        status__in=['pendente', 'atrasado']
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0')

    count_pago = pagamentos.filter(status='pago').count()
    count_pendente = pagamentos.filter(status='pendente').count()
    count_atrasado = pagamentos.filter(status='atrasado').count()
    count_cancelado = pagamentos.filter(status='cancelado').count()

    por_mes = list(
        pagamentos.exclude(mes_referencia__isnull=True).exclude(mes_referencia='')
        .values('mes_referencia')
        .annotate(total=Sum('valor'))
        .order_by('mes_referencia')[:12]
    )

    por_categoria = list(
        pagamentos.exclude(categoria__isnull=True).exclude(categoria='')
        .values('categoria')
        .annotate(total=Sum('valor'))
        .order_by('-total')[:10]
    )

    ultimos_pagamentos = list(
        pagamentos.order_by('-criado_em')[:10].values(
            'id', 'nome', 'valor', 'status', 'data_vencimento', 'categoria', 'mes_referencia'
        )
    )

    ultima_importacao = ImportacaoExcel.objects.order_by('-data_importacao').first()

    return {
        'total_registros': total_registros,
        'total_valor': float(total_valor),
        'total_pago': float(total_pago),
        'total_pendente': float(total_pendente),
        'count_pago': count_pago,
        'count_pendente': count_pendente,
        'count_atrasado': count_atrasado,
        'count_cancelado': count_cancelado,
        'por_mes': [
            {'mes': item['mes_referencia'], 'total': float(item['total'] or 0)}
            for item in por_mes
        ],
        'por_categoria': [
            {'categoria': item['categoria'], 'total': float(item['total'] or 0)}
            for item in por_categoria
        ],
        'ultimos_pagamentos': [
            {
                **item,
                'valor': float(item['valor'] or 0),
                'data_vencimento': str(item['data_vencimento']) if item['data_vencimento'] else None,
            }
            for item in ultimos_pagamentos
        ],
        'ultima_importacao': {
            'data': str(ultima_importacao.data_importacao) if ultima_importacao else None,
            'registros': ultima_importacao.registros_importados if ultima_importacao else 0,
            'sucesso': ultima_importacao.sucesso if ultima_importacao else None,
        } if ultima_importacao else None,
    }


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_calcular_kpis())
        return context


@login_required
def dashboard_api(request):
    dados = _calcular_kpis()
    return JsonResponse(dados)
