from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExcelFileViewSet, ExcelSheetViewSet, ExcelRowViewSet, SyncHistoryViewSet

router = DefaultRouter()
router.register('files', ExcelFileViewSet, basename='excel-file')
router.register('sheets', ExcelSheetViewSet, basename='excel-sheet')
router.register('rows', ExcelRowViewSet, basename='excel-row')
router.register('sync', SyncHistoryViewSet, basename='sync-history')

urlpatterns = [
    path('', include(router.urls)),
]
