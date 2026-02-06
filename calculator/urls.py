from django.urls import path
from . import views

app_name = 'calculator'

urlpatterns = [
    # Калькулятор
    path('', views.CalculatorView.as_view(), name='workspace'),
    path('calculate-all/', views.CalculateAllView.as_view(), name='calculate_all'),
    path('formula/<int:pk>/', views.FormulaCalculatorView.as_view(), name='formula_calculate'),

    # Проекты
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    path('projects/<int:pk>/export/', views.ExportProjectView.as_view(), name='export_project'),

    # Правила генерации
    path('projects/<int:project_id>/rules/add/', views.GenerationRuleCreateView.as_view(), name='rule_create'),
    path('rules/<int:pk>/delete/', views.GenerationRuleDeleteView.as_view(), name='rule_delete'),

    # Варианты
    path('projects/<int:project_id>/generate/', views.GenerateVariantsView.as_view(), name='generate_variants'),
    path('variants/<int:pk>/', views.VariantDetailView.as_view(), name='variant_detail'),
    path('variants/<int:pk>/delete/', views.VariantDeleteView.as_view(), name='variant_delete'),
    path('variants/<int:pk>/recalculate/', views.VariantRecalculateView.as_view(), name='variant_recalculate'),
    path('variants/<int:pk>/export/', views.ExportVariantView.as_view(), name='export_variant'),
]