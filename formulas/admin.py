from django.contrib import admin
from .models import (
    Category, Formula, FormulaVariable, CalculationSession,
    SessionValue, Project, Variant, VariantValue,
    VariantGenerationRule, FormulaChart
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'parent', 'order', 'created_at']
    list_filter = ['user', 'parent']
    search_fields = ['name', 'description']
    ordering = ['user', 'order', 'name']


@admin.register(Formula)
class FormulaAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'user', 'category', 'is_input', 'order', 'updated_at']
    list_filter = ['user', 'is_input', 'category']
    search_fields = ['symbol', 'name', 'expression']
    ordering = ['user', 'symbol']


@admin.register(FormulaVariable)
class FormulaVariableAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'formula', 'var_type', 'source_formula']
    list_filter = ['var_type', 'formula__user']
    search_fields = ['symbol', 'formula__symbol']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at', 'updated_at']
    list_filter = ['user']
    search_fields = ['name', 'description']
    ordering = ['user', '-updated_at']


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ['project', 'number', 'student_name', 'created_at']
    list_filter = ['project__user', 'project']
    search_fields = ['student_name', 'project__name']


@admin.register(VariantValue)
class VariantValueAdmin(admin.ModelAdmin):
    list_display = ['variant', 'formula', 'value', 'is_input']
    list_filter = ['is_input', 'variant__project__user']


@admin.register(VariantGenerationRule)
class VariantGenerationRuleAdmin(admin.ModelAdmin):
    list_display = ['project', 'formula', 'min_value', 'max_value', 'step']
    list_filter = ['project__user']


@admin.register(CalculationSession)
class CalculationSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at', 'updated_at']
    list_filter = ['user']
    search_fields = ['name']


@admin.register(SessionValue)
class SessionValueAdmin(admin.ModelAdmin):
    list_display = ['session', 'formula', 'value', 'is_calculated']
    list_filter = ['session__user', 'is_calculated']


@admin.register(FormulaChart)
class FormulaChartAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'formula', 'chart_type', 'created_at']
    list_filter = ['user', 'chart_type']
    search_fields = ['name']