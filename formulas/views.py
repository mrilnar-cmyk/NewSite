from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
import json

from .models import FormulaHistory
from .models import Category, Formula, FormulaVariable, CalculationSession, SessionValue
from .services import FormulaParser, FormulaCalculator, calculator
from .forms import CategoryForm, FormulaForm

from .models import FormulaChart

from django.http import HttpResponse
from .export import ExcelExporter
from datetime import datetime
from .export import export_full_data

class CategoryListView(ListView):
    """Список категорий"""
    model = Category
    template_name = 'formulas/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        # Только корневые категории (без родителя)
        return Category.objects.filter(parent=None).prefetch_related(
            'children',
            'children__children',  # для подподкатегорий
            'formulas',
            'children__formulas'
        ).order_by('order', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Правильный подсчёт
        all_categories = Category.objects.all()
        context['total_categories'] = all_categories.count()
        context['total_root'] = all_categories.filter(parent=None).count()
        context['total_sub'] = all_categories.exclude(parent=None).count()

        return context

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


class FormulaHistoryListView(ListView):
    """История всех изменений"""
    model = FormulaHistory
    template_name = 'formulas/history_list.html'
    context_object_name = 'history'
    paginate_by = 50

    def get_queryset(self):
        queryset = FormulaHistory.objects.select_related('formula')

        # Фильтр по формуле
        formula_id = self.request.GET.get('formula')
        if formula_id:
            queryset = queryset.filter(formula_id=formula_id)

        # Фильтр по действию
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formulas'] = Formula.objects.all()
        context['selected_formula'] = self.request.GET.get('formula', '')
        context['selected_action'] = self.request.GET.get('action', '')
        return context


class FormulaHistoryDetailView(DetailView):
    """Детали одной записи истории"""
    model = FormulaHistory
    template_name = 'formulas/history_detail.html'
    context_object_name = 'record'

class ChartListView(ListView):
    """Список графиков"""
    model = FormulaChart
    template_name = 'formulas/chart_list.html'
    context_object_name = 'charts'


class ChartCreateView(CreateView):
    """Создание графика"""
    model = FormulaChart
    template_name = 'formulas/chart_form.html'
    fields = ['name', 'formula', 'x_variable', 'x_min', 'x_max', 'x_steps', 'chart_type']
    success_url = reverse_lazy('formulas:chart_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['name'].widget.attrs.update({'class': 'form-control'})
        form.fields['formula'].widget.attrs.update({'class': 'form-select'})
        form.fields['formula'].queryset = Formula.objects.filter(is_input=False)
        form.fields['x_variable'].widget.attrs.update({'class': 'form-control'})
        form.fields['x_min'].widget.attrs.update({'class': 'form-control', 'step': 'any'})
        form.fields['x_max'].widget.attrs.update({'class': 'form-control', 'step': 'any'})
        form.fields['x_steps'].widget.attrs.update({'class': 'form-control', 'min': 10, 'max': 500})
        form.fields['chart_type'].widget.attrs.update({'class': 'form-select'})
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем данные о формулах для JavaScript
        formulas = Formula.objects.filter(is_input=False)
        formulas_with_vars = []
        for f in formulas:
            from .services import FormulaParser
            variables = list(FormulaParser.extract_variables(f.expression)) if f.expression else []
            f.variables_list = variables
            formulas_with_vars.append(f)
        context['formulas'] = formulas_with_vars
        return context

    def form_valid(self, form):
        messages.success(self.request, 'График создан')
        return super().form_valid(form)


class ChartDetailView(DetailView):
    """Просмотр графика с интерактивными параметрами"""
    model = FormulaChart
    template_name = 'formulas/chart_detail.html'
    context_object_name = 'chart'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from .services import FormulaParser

        chart = self.object

        if not chart.formula.expression:
            context['dependent_params'] = []
            context['error'] = "Формула не имеет выражения"
            return context

        all_vars = FormulaParser.extract_variables(chart.formula.expression)
        param_vars = [v for v in all_vars if v != chart.x_variable]

        all_formulas = {f.symbol: f for f in Formula.objects.all()}

        dependent_params = []
        for symbol in sorted(param_vars):
            formula = all_formulas.get(symbol)

            if formula and formula.is_input:
                db_value = formula.default_value

                if db_value is not None:
                    default_val = float(db_value)

                    if default_val > 0:
                        min_val = default_val * 0.1
                        max_val = default_val * 3.0
                    elif default_val < 0:
                        min_val = default_val * 3.0
                        max_val = abs(default_val) * 0.1
                    else:
                        min_val = -10.0
                        max_val = 10.0

                    step = (max_val - min_val) / 100.0
                else:
                    symbol_lower = symbol.lower()

                    if any(x in symbol_lower for x in ['alpha', 'beta', 'gamma', 'theta', 'phi', 'psi', 'angle']):
                        default_val = 10.0
                        min_val = 0.0
                        max_val = 90.0
                        step = 0.5
                    elif symbol_lower.startswith('r') or symbol_lower.startswith('l') or symbol_lower.startswith('h'):
                        default_val = 100.0
                        min_val = 10.0
                        max_val = 500.0
                        step = 5.0
                    else:
                        default_val = 10.0
                        min_val = 0.0
                        max_val = 100.0
                        step = 1.0

                default_val = round(default_val, 4)
                min_val = round(min_val, 4)
                max_val = round(max_val, 4)
                step = round(step, 6)

                if step <= 0:
                    step = 0.01

                dependent_params.append({
                    'symbol': symbol,
                    'name': formula.name,
                    'default_value': default_val,
                    'min_value': min_val,
                    'max_value': max_val,
                    'step': step,
                    'unit': formula.unit or '',
                    'db_value': db_value,
                })

            elif formula and not formula.is_input:
                pass

            else:
                dependent_params.append({
                    'symbol': symbol,
                    'name': f'Параметр {symbol}',
                    'default_value': 10.0,
                    'min_value': 0.0,
                    'max_value': 100.0,
                    'step': 1.0,
                    'unit': '',
                    'db_value': None,
                })

        context['dependent_params'] = dependent_params
        return context


class ChartDataView(View):
    """API: Данные для графика"""

    def post(self, request, pk):
        try:
            chart = get_object_or_404(FormulaChart, pk=pk)
            data = json.loads(request.body)
            fixed_values = data.get('values', {})

            x_min = data.get('x_min')
            x_max = data.get('x_max')

            if x_min is None:
                x_min = chart.x_min
            else:
                x_min = float(x_min)

            if x_max is None:
                x_max = chart.x_max
            else:
                x_max = float(x_max)

            if x_min >= x_max:
                return JsonResponse({
                    'success': False,
                    'error': f'Некорректный диапазон X: {x_min} >= {x_max}'
                })

            float_values = {}
            for key, val in fixed_values.items():
                try:
                    if val is not None and str(val).strip() != '':
                        float_values[key] = float(val)
                except (ValueError, TypeError):
                    pass

            x_values = []
            y_values = []

            steps = chart.x_steps if chart.x_steps >= 2 else 50
            step_size = (x_max - x_min) / (steps - 1)

            all_formulas = list(Formula.objects.all())

            for i in range(steps):
                x = x_min + i * step_size
                x_values.append(round(x, 6))  # 6 знаков

                calc_values = dict(float_values)
                calc_values[chart.x_variable] = x

                try:
                    results = calculator.calculate_formula_with_deps(
                        chart.formula,
                        calc_values,
                        all_formulas
                    )

                    result = results.get(chart.formula.symbol)
                    if result and result.success and result.value is not None:
                        y_values.append(round(result.value, 6))  # 6 знаков
                    else:
                        y_values.append(None)
                except Exception:
                    y_values.append(None)

            return JsonResponse({
                'success': True,
                'x_values': x_values,
                'y_values': y_values,
                'x_label': chart.x_variable,
                'y_label': f"{chart.formula.symbol}" + (f" ({chart.formula.unit})" if chart.formula.unit else ""),
                'title': chart.name,
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Ошибка формата данных'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
class ChartDeleteView(DeleteView):
    """Удаление графика"""
    model = FormulaChart
    template_name = 'formulas/chart_confirm_delete.html'
    success_url = reverse_lazy('formulas:chart_list')


class ExportFormulasView(View):
    """Экспорт всех формул в Excel"""

    def get(self, request):
        formulas = Formula.objects.select_related('category').order_by('category', 'order', 'symbol')

        exporter = ExcelExporter()
        exporter.export_formulas(formulas)

        response = HttpResponse(
            exporter.get_file(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response[
            'Content-Disposition'] = f'attachment; filename="formulas_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx"'

        return response


class UnifiedExportView(View):
    """Единая кнопка экспорта всех данных"""

    def get(self, request):
        """Экспорт всех формул"""
        formulas = Formula.objects.select_related('category').order_by('-is_input', 'category', 'symbol')

        file_data = export_full_data(formulas=formulas)

        response = HttpResponse(
            file_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"formulas_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    def post(self, request):
        """Экспорт с результатами расчёта"""
        try:
            data = json.loads(request.body)
            input_values = {}

            for key, val in data.get('values', {}).items():
                try:
                    if val != '' and val is not None:
                        input_values[key] = float(val)
                except (ValueError, TypeError):
                    pass

            # Формулы
            formulas = list(Formula.objects.select_related('category').order_by('-is_input', 'symbol'))
            formula_map = {f.symbol: f for f in formulas}

            # Вычисляем
            results = calculator.calculate_all(formulas, input_values)

            # Добавляем информацию
            for symbol, result in results.items():
                if symbol in formula_map:
                    result.name = formula_map[symbol].name
                    result.unit = formula_map[symbol].unit

            # Экспортируем
            file_data = export_full_data(
                formulas=formulas,
                calculation_results=results,
                input_values=input_values,
                formula_map=formula_map
            )

            response = HttpResponse(
                file_data,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f"calculation_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


class ChartUpdateView(UpdateView):
    """Редактирование графика"""
    model = FormulaChart
    template_name = 'formulas/chart_form.html'
    fields = ['name', 'formula', 'x_variable', 'x_min', 'x_max', 'x_steps', 'chart_type']

    def get_success_url(self):
        return reverse_lazy('formulas:chart_detail', kwargs={'pk': self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['name'].widget.attrs.update({'class': 'form-control'})
        form.fields['formula'].widget.attrs.update({'class': 'form-select'})
        form.fields['formula'].queryset = Formula.objects.filter(is_input=False)
        form.fields['x_variable'].widget.attrs.update({'class': 'form-control'})
        form.fields['x_min'].widget.attrs.update({'class': 'form-control', 'step': 'any'})
        form.fields['x_max'].widget.attrs.update({'class': 'form-control', 'step': 'any'})
        form.fields['x_steps'].widget.attrs.update({'class': 'form-control', 'min': 10, 'max': 500})
        form.fields['chart_type'].widget.attrs.update({'class': 'form-select'})
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем данные о формулах для JavaScript
        formulas = Formula.objects.filter(is_input=False)
        formulas_with_vars = []
        for f in formulas:
            from .services import FormulaParser
            variables = list(FormulaParser.extract_variables(f.expression)) if f.expression else []
            f.variables_list = variables
            formulas_with_vars.append(f)
        context['formulas'] = formulas_with_vars
        return context

    def form_valid(self, form):
        messages.success(self.request, 'График обновлён')
        return super().form_valid(form)