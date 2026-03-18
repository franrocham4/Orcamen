import logging
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

from .models import Pagamento, ImportacaoExcel

logger = logging.getLogger(__name__)


class PagamentosListView(LoginRequiredMixin, ListView):
    model = Pagamento
    template_name = 'pagamentos/lista.html'
    context_object_name = 'pagamentos'
    paginate_by = 50

    def get_queryset(self):
        qs = Pagamento.objects.all()
        status = self.request.GET.get('status')
        mes = self.request.GET.get('mes')
        categoria = self.request.GET.get('categoria')
        busca = self.request.GET.get('busca')

        if status:
            qs = qs.filter(status=status)
        if mes:
            qs = qs.filter(mes_referencia=mes)
        if categoria:
            qs = qs.filter(categoria=categoria)
        if busca:
            qs = qs.filter(
                Q(nome__icontains=busca) |
                Q(fornecedor__icontains=busca) |
                Q(descricao__icontains=busca) |
                Q(referencia__icontains=busca) |
                Q(numero_nf__icontains=busca)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Pagamento.STATUS_CHOICES
        context['meses'] = (
            Pagamento.objects.exclude(mes_referencia__isnull=True)
            .exclude(mes_referencia='')
            .values_list('mes_referencia', flat=True)
            .distinct()
            .order_by('mes_referencia')
        )
        context['categorias'] = (
            Pagamento.objects.exclude(categoria__isnull=True)
            .exclude(categoria='')
            .values_list('categoria', flat=True)
            .distinct()
            .order_by('categoria')
        )
        context['filtros'] = {
            'status': self.request.GET.get('status', ''),
            'mes': self.request.GET.get('mes', ''),
            'categoria': self.request.GET.get('categoria', ''),
            'busca': self.request.GET.get('busca', ''),
        }
        return context


class PagamentoDetailView(LoginRequiredMixin, DetailView):
    model = Pagamento
    template_name = 'pagamentos/detalhe.html'
    context_object_name = 'pagamento'


class ImportacoesListView(LoginRequiredMixin, ListView):
    model = ImportacaoExcel
    template_name = 'pagamentos/importacoes.html'
    context_object_name = 'importacoes'
    paginate_by = 20
