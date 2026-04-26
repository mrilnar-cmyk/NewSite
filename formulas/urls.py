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

    # Графики
    path('charts/', views.ChartListView.as_view(), name='chart_list'),
    path('charts/create/', views.ChartCreateView.as_view(), name='chart_create'),
    path('charts/<int:pk>/', views.ChartDetailView.as_view(), name='chart_detail'),
    path('charts/<int:pk>/data/', views.ChartDataView.as_view(), name='chart_data'),
    path('charts/<int:pk>/delete/', views.ChartDeleteView.as_view(), name='chart_delete'),
    path('charts/<int:pk>/edit/', views.ChartUpdateView.as_view(), name='chart_edit'),

    # Экспорт
    path('export/', views.UnifiedExportView.as_view(), name='export'),

    # Чат-бот
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('chat/send/', views.ChatSendView.as_view(), name='chat_send'),
    path('chat/clear/', views.ChatClearView.as_view(), name='chat_clear'),

    # API
    path('api/parse/', views.ParseFormulaView.as_view(), name='api_parse'),
    path('api/calculate/', views.CalculateFormulaView.as_view(), name='api_calculate'),
    path('api/quick-calculate/', views.QuickCalculateView.as_view(), name='api_quick_calculate'),
    path('api/latex-preview/', views.latex_preview_api, name='latex_preview_api'),
    path('api/latex-preview-batch/', views.latex_preview_batch_api, name='latex_preview_batch_api'),
]