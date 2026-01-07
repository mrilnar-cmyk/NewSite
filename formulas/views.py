from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
import json

from .models import Category, Formula, FormulaVariable, CalculationSession, SessionValue
from .services import FormulaParser, FormulaCalculator, calculator
from .forms import CategoryForm, FormulaForm


class CategoryListView(ListView):
    """Список категорий"""
    model = Category
    template_name = 'formulas/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(parent=None).prefetch_related('children', 'formulas')


class CategoryCreateView(CreateView):
    """Создание категории"""
    model = Category
    form_class = CategoryForm
    template_name = 'formulas/category_form.html'
    success_url = reverse_lazy('formulas:category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Категория успешно создана')
        return super().form_valid(form)


class CategoryUpdateView(UpdateView):
    """Редактирование категории"""
    model = Category
    form_class = CategoryForm
    template_name = 'formulas/category_form.html'
    success_url = reverse_lazy('formulas:category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Категория успешно обновлена')
        return super().form_valid(form)


class CategoryDeleteView(DeleteView):
    """Удаление категории"""
    model = Category
    template_name = 'formulas/category_confirm_delete.html'
    success_url = reverse_lazy('formulas:category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Категория удалена')
        return super().form_valid(form)


class FormulaListView(ListView):
    """Список формул с поиском и фильтрацией"""
    model = Formula
    template_name = 'formulas/formula_list.html'
    context_object_name = 'formulas'
    paginate_by = 25

    def get_queryset(self):
        queryset = Formula.objects.select_related('category').prefetch_related('variables')

        # Поиск
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(symbol__icontains=search) |
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(expression__icontains=search)
            )

        # Фильтр по категории
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Фильтр: только входные параметры
        is_input = self.request.GET.get('is_input')
        if is_input == '1':
            queryset = queryset.filter(is_input=True)
        elif is_input == '0':
            queryset = queryset.filter(is_input=False)

        return queryset.order_by('category', 'order', 'symbol')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['search'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['total_count'] = Formula.objects.count()
        return context


class FormulaDetailView(DetailView):
    """Детальный просмотр формулы"""
    model = Formula
    template_name = 'formulas/formula_detail.html'
    context_object_name = 'formula'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Получаем переменные
        variables = FormulaParser.extract_variables(self.object.expression)
        context['extracted_variables'] = variables

        # Формулы, которые используют эту формулу
        context['used_in'] = Formula.objects.filter(
            expression__contains=self.object.symbol
        ).exclude(pk=self.object.pk)

        # Формулы, от которых зависит эта формула
        all_formulas = Formula.objects.all()
        formula_symbols = {f.symbol for f in all_formulas}
        dependencies = [
            var for var in variables
            if var in formula_symbols
        ]
        context['dependencies'] = Formula.objects.filter(symbol__in=dependencies)

        return context


class FormulaCreateView(CreateView):
    """Создание формулы"""
    model = Formula
    form_class = FormulaForm
    template_name = 'formulas/formula_form.html'
    success_url = reverse_lazy('formulas:formula_list')

    def form_valid(self, form):
        messages.success(self.request, f'Формула "{form.instance.symbol}" успешно создана')
        response = super().form_valid(form)

        # Автоматически создаём переменные (только для вычисляемых формул)
        if not self.object.is_input and self.object.expression:
            self._create_variables(self.object)

        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Ошибка при создании формулы. Проверьте введённые данные.')
        return super().form_invalid(form)

    def _create_variables(self, formula):
        """Создаёт переменные на основе выражения"""
        from .services import FormulaParser

        try:
            variables = FormulaParser.extract_variables(formula.expression)
            all_formulas = {f.symbol: f for f in Formula.objects.exclude(pk=formula.pk)}

            for var_symbol in variables:
                var_type = 'formula' if var_symbol in all_formulas else 'input'
                source = all_formulas.get(var_symbol)

                FormulaVariable.objects.create(
                    formula=formula,
                    symbol=var_symbol,
                    var_type=var_type,
                    source_formula=source
                )
        except Exception as e:
            print(f"Ошибка создания переменных: {e}")


class FormulaUpdateView(UpdateView):
    """Редактирование формулы"""
    model = Formula
    form_class = FormulaForm
    template_name = 'formulas/formula_form.html'

    def get_success_url(self):
        return reverse_lazy('formulas:formula_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Формула "{form.instance.symbol}" обновлена')
        response = super().form_valid(form)

        # Обновляем переменные
        self.object.variables.all().delete()

        if not self.object.is_input and self.object.expression:
            self._create_variables(self.object)

        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Ошибка при обновлении формулы.')
        return super().form_invalid(form)

    def _create_variables(self, formula):
        """Создаёт переменные на основе выражения"""
        from .services import FormulaParser

        try:
            variables = FormulaParser.extract_variables(formula.expression)
            all_formulas = {f.symbol: f for f in Formula.objects.exclude(pk=formula.pk)}

            for var_symbol in variables:
                var_type = 'formula' if var_symbol in all_formulas else 'input'
                source = all_formulas.get(var_symbol)

                FormulaVariable.objects.create(
                    formula=formula,
                    symbol=var_symbol,
                    var_type=var_type,
                    source_formula=source
                )
        except Exception as e:
            print(f"Ошибка создания переменных: {e}")


class FormulaDeleteView(DeleteView):
    """Удаление формулы"""
    model = Formula
    template_name = 'formulas/formula_confirm_delete.html'
    success_url = reverse_lazy('formulas:formula_list')

    def form_valid(self, form):
        symbol = self.object.symbol
        response = super().form_valid(form)
        messages.success(self.request, f'Формула "{symbol}" удалена')
        return response


# === API для AJAX ===

class ParseFormulaView(View):
    """API: Парсинг формулы и извлечение переменных"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            expression = data.get('expression', '')

            # Валидация
            is_valid, error = FormulaParser.validate_expression(expression)
            if not is_valid:
                return JsonResponse({
                    'success': False,
                    'error': error
                })

            # Извлекаем переменные
            variables = list(FormulaParser.extract_variables(expression))

            # Проверяем, какие из переменных - это другие формулы
            existing_formulas = Formula.objects.filter(symbol__in=variables)
            formula_symbols = {f.symbol for f in existing_formulas}

            variable_info = []
            for var in sorted(variables):
                variable_info.append({
                    'symbol': var,
                    'is_formula': var in formula_symbols,
                    'source_formula': var if var in formula_symbols else None
                })

            return JsonResponse({
                'success': True,
                'variables': variable_info
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Некорректный JSON'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class CalculateFormulaView(View):
    """API: Вычисление формулы"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            formula_id = data.get('formula_id')
            values = data.get('values', {})

            # Преобразуем значения в float
            float_values = {}
            for key, val in values.items():
                try:
                    if val != '' and val is not None:
                        float_values[key] = float(val)
                except (ValueError, TypeError):
                    return JsonResponse({
                        'success': False,
                        'error': f'Некорректное значение для {key}: {val}'
                    })

            # Получаем формулу
            formula = get_object_or_404(Formula, pk=formula_id)

            # Получаем все формулы для разрешения зависимостей
            all_formulas = list(Formula.objects.all())

            # Вычисляем с зависимостями (используем правильное имя метода)
            results = calculator.calculate_formula_with_deps(
                formula,
                float_values,
                all_formulas
            )

            # Форматируем результат
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

            # Главный результат
            main_result = results.get(formula.symbol)
            if main_result:
                response_data['main_result'] = {
                    'symbol': formula.symbol,
                    'value': main_result.value,
                    'unit': formula.unit,
                    'success': main_result.success,
                    'error': main_result.error
                }

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Некорректный JSON'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class QuickCalculateView(View):
    """API: Быстрое вычисление выражения без сохранения"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            expression = data.get('expression', '')
            values = data.get('values', {})

            # Преобразуем значения в float
            float_values = {}
            for key, val in values.items():
                try:
                    float_values[key] = float(val)
                except (ValueError, TypeError):
                    return JsonResponse({
                        'success': False,
                        'error': f'Некорректное значение для {key}: {val}'
                    })

            # Вычисляем
            result = calculator.calculate_single(expression, float_values)

            return JsonResponse({
                'success': result.success,
                'value': result.value,
                'error': result.error
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })