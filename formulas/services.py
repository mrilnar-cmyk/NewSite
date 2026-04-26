import re
import math
import random
from typing import Dict, Any, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CalculationResult:
    """Результат вычисления одной формулы"""
    symbol: str
    value: Optional[float]
    success: bool
    error: Optional[str] = None
    formula_expression: str = ""
    dependencies: List[str] = field(default_factory=list)


class FormulaParser:
    """Парсер для извлечения переменных из формулы"""

    BUILTIN_FUNCTIONS = {
        'sin', 'cos', 'tan', 'tg', 'ctg', 'cot',
        'asin', 'acos', 'atan', 'atan2',
        'sinh', 'cosh', 'tanh',
        'sqrt', 'cbrt', 'root',
        'log', 'ln', 'log10', 'log2', 'exp',
        'abs', 'round', 'ceil', 'floor',
        'min', 'max', 'sum', 'avg',
        'pow', 'mod',
        'if_else', 'rad', 'deg',
        'pi', 'e',
    }

    @classmethod
    def extract_variables(cls, expression: str) -> Set[str]:
        if not expression:
            return set()
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        matches = re.findall(pattern, expression)
        variables = {
            match for match in matches
            if match.lower() not in cls.BUILTIN_FUNCTIONS
        }
        return variables

    @classmethod
    def validate_expression(cls, expression: str) -> Tuple[bool, Optional[str]]:
        if not expression or not expression.strip():
            return False, "Выражение не может быть пустым"

        open_count = expression.count('(')
        close_count = expression.count(')')
        if open_count != close_count:
            return False, f"Несбалансированные скобки: ( = {open_count}, ) = {close_count}"

        forbidden = ['import', 'exec', 'eval', '__', 'open', 'file', 'os.']
        for item in forbidden:
            if item in expression.lower():
                return False, f"Запрещённая конструкция: {item}"

        return True, None


class FormulaCalculator:
    """Движок вычисления формул с каскадными зависимостями"""

    def __init__(self, angle_unit: str = 'degrees', decimal_places: int = 8):
        self.angle_unit = angle_unit
        self.decimal_places = decimal_places

    def _to_radians(self, angle: float) -> float:
        if self.angle_unit == 'degrees':
            return math.radians(angle)
        return angle

    def _create_safe_environment(self, variables: Dict[str, float]) -> Dict[str, Any]:
        def safe_sin(x):
            return math.sin(self._to_radians(x))

        def safe_cos(x):
            return math.cos(self._to_radians(x))

        def safe_tan(x):
            return math.tan(self._to_radians(x))

        def safe_tg(x):
            return math.tan(self._to_radians(x))

        def safe_ctg(x):
            return 1 / math.tan(self._to_radians(x))

        def safe_asin(x):
            result = math.asin(x)
            if self.angle_unit == 'degrees':
                return math.degrees(result)
            return result

        def safe_acos(x):
            result = math.acos(x)
            if self.angle_unit == 'degrees':
                return math.degrees(result)
            return result

        def safe_atan(x):
            result = math.atan(x)
            if self.angle_unit == 'degrees':
                return math.degrees(result)
            return result

        def if_else(condition, true_value, false_value):
            return true_value if condition else false_value

        def root(x, n):
            return x ** (1 / n)

        def avg(*args):
            return sum(args) / len(args)

        safe_env = {
            '__builtins__': {},
            'pi': math.pi, 'PI': math.pi,
            'e': math.e, 'E': math.e,
            'sin': safe_sin, 'cos': safe_cos,
            'tan': safe_tan, 'tg': safe_tg,
            'ctg': safe_ctg, 'cot': safe_ctg,
            'asin': safe_asin, 'acos': safe_acos, 'atan': safe_atan,
            'sinh': math.sinh, 'cosh': math.cosh, 'tanh': math.tanh,
            'sqrt': math.sqrt,
            'cbrt': lambda x: x ** (1 / 3) if x >= 0 else -((-x) ** (1 / 3)),
            'root': root, 'pow': pow,
            'log': math.log, 'ln': math.log,
            'log10': math.log10, 'log2': math.log2, 'exp': math.exp,
            'abs': abs, 'round': round,
            'ceil': math.ceil, 'floor': math.floor,
            'min': min, 'max': max, 'sum': sum, 'avg': avg,
            'mod': lambda x, y: x % y,
            'if_else': if_else,
            'rad': math.radians, 'deg': math.degrees,
            **variables,
        }
        return safe_env

    def _prepare_expression(self, expression: str) -> str:
        expr = expression.strip()
        expr = re.sub(r'\^', '**', expr)
        expr = re.sub(r'\bif\s*\(', 'if_else(', expr)
        return expr

    def calculate_single(self, expression: str, variables: Dict[str, float]) -> CalculationResult:
        is_valid, error = FormulaParser.validate_expression(expression)
        if not is_valid:
            return CalculationResult(
                symbol="", value=None, success=False,
                error=error, formula_expression=expression
            )

        prepared_expr = self._prepare_expression(expression)
        safe_env = self._create_safe_environment(variables)

        try:
            result = eval(prepared_expr, safe_env)
            if isinstance(result, float):
                result = round(result, self.decimal_places)

            return CalculationResult(
                symbol="", value=float(result), success=True,
                formula_expression=expression
            )
        except NameError as e:
            missing_var = str(e).split("'")[1] if "'" in str(e) else str(e)
            return CalculationResult(
                symbol="", value=None, success=False,
                error=f"Неизвестная переменная: {missing_var}",
                formula_expression=expression
            )
        except ZeroDivisionError:
            return CalculationResult(
                symbol="", value=None, success=False,
                error="Деление на ноль", formula_expression=expression
            )
        except ValueError as e:
            return CalculationResult(
                symbol="", value=None, success=False,
                error=f"Математическая ошибка: {e}",
                formula_expression=expression
            )
        except Exception as e:
            return CalculationResult(
                symbol="", value=None, success=False,
                error=f"Ошибка вычисления: {e}",
                formula_expression=expression
            )

    def build_dependency_graph(self, formulas: List['Formula']) -> Dict[str, List[str]]:
        """Строит граф зависимостей формул"""
        graph = {}
        formula_symbols = {f.symbol for f in formulas}

        for formula in formulas:
            if formula.is_input or not formula.expression:
                graph[formula.symbol] = []
            else:
                deps = FormulaParser.extract_variables(formula.expression)
                graph[formula.symbol] = [d for d in deps if d in formula_symbols]

        return graph

    def topological_sort(self, formulas: List['Formula']) -> List['Formula']:
        """Топологическая сортировка формул по зависимостям"""
        graph = self.build_dependency_graph(formulas)
        formula_map = {f.symbol: f for f in formulas}

        visited = set()
        temp_visited = set()
        order = []

        def visit(symbol: str):
            if symbol in temp_visited:
                return  # Циклическая зависимость
            if symbol in visited:
                return

            temp_visited.add(symbol)

            for dep in graph.get(symbol, []):
                if dep in formula_map:
                    visit(dep)

            temp_visited.remove(symbol)
            visited.add(symbol)

            if symbol in formula_map:
                order.append(formula_map[symbol])

        for formula in formulas:
            visit(formula.symbol)

        return order

    def calculate_all(
            self,
            formulas: List['Formula'],
            input_values: Dict[str, float]
    ) -> Dict[str, CalculationResult]:
        """
        Вычисляет ВСЕ формулы в правильном порядке
        """
        sorted_formulas = self.topological_sort(formulas)
        results = {}
        current_values = dict(input_values)

        for formula in sorted_formulas:
            if formula.is_input:
                # Входной параметр
                value = current_values.get(formula.symbol, formula.default_value)
                results[formula.symbol] = CalculationResult(
                    symbol=formula.symbol,
                    value=value,
                    success=value is not None,
                    formula_expression="(входной параметр)",
                    error=None if value is not None else "Значение не задано"
                )
                if value is not None:
                    current_values[formula.symbol] = value
            else:
                # Вычисляемая формула
                if not formula.expression:
                    results[formula.symbol] = CalculationResult(
                        symbol=formula.symbol, value=None, success=False,
                        error="Выражение не задано", formula_expression=""
                    )
                    continue

                result = self.calculate_single(formula.expression, current_values)
                result.symbol = formula.symbol
                results[formula.symbol] = result

                if result.success and result.value is not None:
                    current_values[formula.symbol] = result.value

        return results

    def calculate_formula_with_deps(
            self,
            target_formula: 'Formula',
            input_values: Dict[str, float],
            all_formulas: List['Formula']
    ) -> Dict[str, CalculationResult]:
        """
        Вычисляет конкретную формулу и все её зависимости
        """
        # Находим все зависимости рекурсивно
        formula_map = {f.symbol: f for f in all_formulas}
        needed_symbols = set()

        def collect_deps(symbol: str):
            if symbol in needed_symbols:
                return
            needed_symbols.add(symbol)

            if symbol in formula_map:
                formula = formula_map[symbol]
                if not formula.is_input and formula.expression:
                    deps = FormulaParser.extract_variables(formula.expression)
                    for dep in deps:
                        collect_deps(dep)

        collect_deps(target_formula.symbol)

        # Фильтруем только нужные формулы
        needed_formulas = [f for f in all_formulas if f.symbol in needed_symbols]

        return self.calculate_all(needed_formulas, input_values)


class VariantGenerator:
    """Генератор вариантов заданий"""

    def __init__(self, project: 'Project'):
        self.project = project

    def generate_values(self, rules: List['VariantGenerationRule']) -> Dict[str, float]:
        """Генерирует случайные значения по правилам"""
        values = {}
        for rule in rules:
            if rule.step > 0:
                # Генерация с шагом
                steps = int((rule.max_value - rule.min_value) / rule.step) + 1
                step_index = random.randint(0, steps - 1)
                value = rule.min_value + step_index * rule.step
            else:
                # Случайное значение в диапазоне
                value = random.uniform(rule.min_value, rule.max_value)

            values[rule.formula.symbol] = round(value, 4)

        return values

    def create_formulas_snapshot(self, formulas: List['Formula']) -> dict:
        """Создает JSON-снимок всех формул для сохранения в варианте"""
        snapshot = {}
        for formula in formulas:
            snapshot[formula.symbol] = {
                'name': formula.name,
                'expression': formula.expression,
                'unit': formula.unit,
                'is_input': formula.is_input,
                'description': formula.description,
            }
        return snapshot

    def generate_variants(self, count: int) -> List['Variant']:
        """Генерирует указанное количество вариантов"""
        from .models import Variant, VariantValue, VariantGenerationRule, Formula

        rules = list(self.project.generation_rules.select_related('formula'))
        if not rules:
            return []

        calculator = FormulaCalculator()
        
        #Только формулы текущего пользователя
        all_formulas = list(Formula.objects.filter(user=self.project.user).select_related('category'))

        # Находим следующий номер варианта
        last_variant = self.project.variants.order_by('-number').first()
        start_number = (last_variant.number + 1) if last_variant else 1

        created_variants = []

        for i in range(count):
            # Генерируем входные значения
            input_values = self.generate_values(rules)

            # ВЕРСИОНИРОВАНИЕ: Создаем снимок формул
            formulas_snapshot = self.create_formulas_snapshot(all_formulas)

            # Создаём вариант
            variant = Variant.objects.create(
                project=self.project,
                number=start_number + i,
                formulas_snapshot=formulas_snapshot  # Сохраняем снимок
            )

            # Вычисляем все формулы
            results = calculator.calculate_all(all_formulas, input_values)

            # Сохраняем значения
            for symbol, result in results.items():
                formula = next((f for f in all_formulas if f.symbol == symbol), None)
                
                # ИСПРАВЛЕНИЕ 2: Проверяем принадлежность формулы
                if formula and formula.user == self.project.user and result.value is not None:
                    VariantValue.objects.create(
                        variant=variant,
                        formula=formula,
                        value=result.value,
                        is_input=formula.is_input
                    )

            created_variants.append(variant)

        return created_variants


# Глобальный экземпляр калькулятора
calculator = FormulaCalculator(angle_unit='degrees', decimal_places=8)