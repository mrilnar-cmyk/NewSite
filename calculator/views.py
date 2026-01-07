from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
import json

from formulas.models import (
    Formula, Category, Project, Variant, VariantValue,
    VariantGenerationRule, CalculationSession, SessionValue
)
from formulas.services import FormulaParser, FormulaCalculator, VariantGenerator, calculator


class CalculatorView(View):
    """Главная страница калькулятора"""

    def get(self, request):
        formulas = Formula.objects.select_related('category').order_by('category', 'order', 'symbol')
        categories = Category.objects.filter(parent=None)

        formulas_by_category = {}
        uncategorized = []

        for formula in formulas:
            if formula.category:
                cat_name = formula.category.name
                if cat_name not in formulas_by_category:
                    formulas_by_category[cat_name] = []
                formulas_by_category[cat_name].append(formula)
            else:
                uncategorized.append(formula)

        if uncategorized:
            formulas_by_category['Без категории'] = uncategorized

        context = {
            'formulas': formulas,
            'categories': categories,
            'formulas_by_category': formulas_by_category,
            'projects': Project.objects.all()[:5],
        }
        return render(request, 'calculator/workspace.html', context)


class CalculateAllView(View):
    """Страница вычисления ВСЕХ формул сразу"""

    def get(self, request):
        formulas = Formula.objects.select_related('category').order_by('category', 'order', 'symbol')
        input_formulas = [f for f in formulas if f.is_input]
        calculated_formulas = [f for f in formulas if not f.is_input]

        # Загружаем сохранённые значения из сессии
        session_values = request.session.get('calculator_values', {})

        context = {
            'input_formulas': input_formulas,
            'calculated_formulas': calculated_formulas,
            'all_formulas': formulas,
            'session_values': session_values,
        }
        return render(request, 'calculator/calculate_all.html', context)

    def post(self, request):
        """AJAX вычисление всех формул"""
        try:
            data = json.loads(request.body)
            input_values = {}

            # Преобразуем входные значения
            for key, val in data.get('values', {}).items():
                try:
                    if val != '' and val is not None:
                        input_values[key] = float(val)
                except (ValueError, TypeError):
                    pass

            # Сохраняем в сессию
            request.session['calculator_values'] = {k: str(v) for k, v in input_values.items()}

            # Вычисляем все формулы
            all_formulas = list(Formula.objects.all())
            results = calculator.calculate_all(all_formulas, input_values)

            # Форматируем ответ
            response_data = {
                'success': True,
                'results': {}
            }

            for symbol, result in results.items():
                response_data['results'][symbol] = {
                    'value': result.value,
                    'success': result.success,
                    'error': result.error,
                    'expression': result.formula_expression
                }

            return JsonResponse(response_data)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class FormulaCalculatorView(View):
    """Страница вычисления конкретной формулы"""

    def get(self, request, pk):
        formula = get_object_or_404(Formula, pk=pk)
        all_formulas = list(Formula.objects.all())

        # Определяем зависимости
        dependencies = []
        if not formula.is_input and formula.expression:
            dep_symbols = FormulaParser.extract_variables(formula.expression)
            formula_map = {f.symbol: f for f in all_formulas}

            def collect_deps(symbol, depth=0):
                if symbol in formula_map and depth < 10:
                    f = formula_map[symbol]
                    if f.symbol != formula.symbol:
                        dependencies.append(f)
                        if not f.is_input and f.expression:
                            for dep in FormulaParser.extract_variables(f.expression):
                                collect_deps(dep, depth + 1)

            for dep in dep_symbols:
                collect_deps(dep)

        # Уникальные зависимости
        seen = set()
        unique_deps = []
        for d in dependencies:
            if d.symbol not in seen:
                seen.add(d.symbol)
                unique_deps.append(d)

        # Загружаем сохранённые значения
        session_values = request.session.get('calculator_values', {})

        context = {
            'formula': formula,
            'dependencies': unique_deps,
            'all_formulas': all_formulas,
            'session_values': session_values,
        }
        return render(request, 'calculator/formula_calculate.html', context)


# ==================== ПРОЕКТЫ И ВАРИАНТЫ ====================

class ProjectListView(ListView):
    """Список проектов"""
    model = Project
    template_name = 'calculator/project_list.html'
    context_object_name = 'projects'


class ProjectCreateView(CreateView):
    """Создание проекта"""
    model = Project
    template_name = 'calculator/project_form.html'
    fields = ['name', 'description']
    success_url = reverse_lazy('calculator:project_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['name'].widget.attrs.update({'class': 'form-control'})
        form.fields['description'].widget.attrs.update({'class': 'form-control', 'rows': 3})
        return form

    def form_valid(self, form):
        messages.success(self.request, 'Проект создан')
        return super().form_valid(form)


class ProjectDetailView(DetailView):
    """Детали проекта с вариантами"""
    model = Project
    template_name = 'calculator/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['variants'] = self.object.variants.all()
        context['rules'] = self.object.generation_rules.select_related('formula')
        context['input_formulas'] = Formula.objects.filter(is_input=True)
        return context


class ProjectDeleteView(DeleteView):
    """Удаление проекта"""
    model = Project
    template_name = 'calculator/project_confirm_delete.html'
    success_url = reverse_lazy('calculator:project_list')


class GenerationRuleCreateView(View):
    """Добавление правила генерации"""

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)

        formula_id = request.POST.get('formula')
        min_val = request.POST.get('min_value')
        max_val = request.POST.get('max_value')
        step = request.POST.get('step', 1)

        try:
            formula = Formula.objects.get(pk=formula_id)

            VariantGenerationRule.objects.update_or_create(
                project=project,
                formula=formula,
                defaults={
                    'min_value': float(min_val),
                    'max_value': float(max_val),
                    'step': float(step) if step else 1,
                }
            )
            messages.success(request, f'Правило для {formula.symbol} добавлено')
        except Exception as e:
            messages.error(request, f'Ошибка: {e}')

        return redirect('calculator:project_detail', pk=project_id)


class GenerationRuleDeleteView(View):
    """Удаление правила генерации"""

    def post(self, request, pk):
        rule = get_object_or_404(VariantGenerationRule, pk=pk)
        project_id = rule.project.id
        rule.delete()
        messages.success(request, 'Правило удалено')
        return redirect('calculator:project_detail', pk=project_id)


class GenerateVariantsView(View):
    """Генерация вариантов"""

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)

        try:
            count = int(request.POST.get('count', 1))
            count = min(count, 100)  # Ограничение

            generator = VariantGenerator(project)
            variants = generator.generate_variants(count)

            messages.success(request, f'Создано {len(variants)} вариантов')
        except Exception as e:
            messages.error(request, f'Ошибка: {e}')

        return redirect('calculator:project_detail', pk=project_id)


class VariantDetailView(DetailView):
    """Детали варианта"""
    model = Variant
    template_name = 'calculator/variant_detail.html'
    context_object_name = 'variant'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Группируем значения
        values = self.object.values.select_related('formula', 'formula__category')

        input_values = [v for v in values if v.is_input]
        calculated_values = [v for v in values if not v.is_input]

        context['input_values'] = input_values
        context['calculated_values'] = calculated_values

        return context


class VariantDeleteView(View):
    """Удаление варианта"""

    def post(self, request, pk):
        variant = get_object_or_404(Variant, pk=pk)
        project_id = variant.project.id
        variant.delete()
        messages.success(request, 'Вариант удалён')
        return redirect('calculator:project_detail', pk=project_id)


class VariantRecalculateView(View):
    """Пересчёт варианта"""

    def post(self, request, pk):
        variant = get_object_or_404(Variant, pk=pk)

        # Собираем входные значения
        input_values = {}
        for vv in variant.values.filter(is_input=True).select_related('formula'):
            input_values[vv.formula.symbol] = vv.value

        # Пересчитываем
        all_formulas = list(Formula.objects.all())
        results = calculator.calculate_all(all_formulas, input_values)

        # Обновляем значения
        for symbol, result in results.items():
            if result.success and result.value is not None:
                formula = next((f for f in all_formulas if f.symbol == symbol), None)
                if formula:
                    VariantValue.objects.update_or_create(
                        variant=variant,
                        formula=formula,
                        defaults={
                            'value': result.value,
                            'is_input': formula.is_input
                        }
                    )

        messages.success(request, 'Вариант пересчитан')
        return redirect('calculator:variant_detail', pk=pk)