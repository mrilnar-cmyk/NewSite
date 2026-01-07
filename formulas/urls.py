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

    # API
    path('api/parse/', views.ParseFormulaView.as_view(), name='api_parse'),
    path('api/calculate/', views.CalculateFormulaView.as_view(), name='api_calculate'),
    path('api/quick-calculate/', views.QuickCalculateView.as_view(), name='api_quick_calculate'),
]