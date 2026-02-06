from django.urls import path
from . import views

app_name = 'formulas'

urlpatterns = [
    # Категории
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Формулы
    path('', views.FormulaListView.as_view(), name='formula_list'),
    path('<int:pk>/', views.FormulaDetailView.as_view(), name='formula_detail'),
    path('create/', views.FormulaCreateView.as_view(), name='formula_create'),
    path('<int:pk>/edit/', views.FormulaUpdateView.as_view(), name='formula_edit'),
    path('<int:pk>/delete/', views.FormulaDeleteView.as_view(), name='formula_delete'),
    path('history/', views.FormulaHistoryListView.as_view(), name='history_list'),
    path('history/<int:pk>/', views.FormulaHistoryDetailView.as_view(), name='history_detail'),

    # Графики
    path('charts/', views.ChartListView.as_view(), name='chart_list'),
    path('charts/create/', views.ChartCreateView.as_view(), name='chart_create'),
    path('charts/<int:pk>/', views.ChartDetailView.as_view(), name='chart_detail'),
    path('charts/<int:pk>/data/', views.ChartDataView.as_view(), name='chart_data'),
    path('charts/<int:pk>/delete/', views.ChartDeleteView.as_view(), name='chart_delete'),
    path('charts/<int:pk>/edit/', views.ChartUpdateView.as_view(), name='chart_edit'),

    # Экспорт
    path('export/', views.UnifiedExportView.as_view(), name='export'),

    # API
    path('api/parse/', views.ParseFormulaView.as_view(), name='api_parse'),
    path('api/calculate/', views.CalculateFormulaView.as_view(), name='api_calculate'),
    path('api/quick-calculate/', views.QuickCalculateView.as_view(), name='api_quick_calculate'),
]