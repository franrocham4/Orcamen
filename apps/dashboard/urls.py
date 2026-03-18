from django.urls import path
from .views import (DashboardView, SheetsListView, SheetDetailView,
                    SincronizarView, SyncStatusView, IndexView)

app_name = 'dashboard'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/sheets/', SheetsListView.as_view(), name='sheets_list'),
    path('dashboard/sheets/<int:sheet_id>/', SheetDetailView.as_view(), name='sheet_detail'),
    path('dashboard/sincronizar/', SincronizarView.as_view(), name='sincronizar'),
    path('dashboard/sync-status/', SyncStatusView.as_view(), name='sync_status'),
]
