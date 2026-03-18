from django.urls import path
from . import views

app_name = 'pagamentos'

urlpatterns = [
    path('', views.PagamentosListView.as_view(), name='lista'),
    path('<int:pk>/', views.PagamentoDetailView.as_view(), name='detalhe'),
    path('importacoes/', views.ImportacoesListView.as_view(), name='importacoes'),
]
