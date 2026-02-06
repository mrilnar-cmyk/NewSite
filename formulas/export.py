import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter


class ExcelExporter:
    """Универсальный экспорт данных в Excel"""

    def __init__(self):
        self.wb = Workbook()
        # Удаляем дефолтный лист
        self.wb.remove(self.wb.active)

        # Стили
        self.header_font = Font(bold=True, color="FFFFFF", size=11)
        self.header_fill = PatternFill(start_color="0d6efd", end_color="0d6efd", fill_type="solid")
        self.header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        self.subheader_font = Font(bold=True, size=10)
        self.subheader_fill = PatternFill(start_color="6c757d", end_color="6c757d", fill_type="solid")

        self.cell_alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        self.number_alignment = Alignment(horizontal="right", vertical="center")
        self.center_alignment = Alignment(horizontal="center", vertical="center")

        self.thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        self.input_fill = PatternFill(start_color="d4edda", end_color="d4edda", fill_type="solid")  # Зелёный
        self.calc_fill = PatternFill(start_color="fff3cd", end_color="fff3cd", fill_type="solid")  # Жёлтый
        self.title_fill = PatternFill(start_color="e9ecef", end_color="e9ecef", fill_type="solid")  # Серый

    def _apply_header_style(self, cell):
        cell.font = self.header_font
        cell.fill = self.header_fill
        cell.alignment = self.header_alignment
        cell.border = self.thin_border

    def _apply_cell_style(self, cell, is_number=False, is_input=None):
        cell.alignment = self.number_alignment if is_number else self.cell_alignment
        cell.border = self.thin_border
        if is_input is True:
            cell.fill = self.input_fill
        elif is_input is False:
            cell.fill = self.calc_fill

    def _auto_width(self, ws, min_width=10, max_width=50):
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)

            for cell in column:
                try:
                    if cell.value:
                        cell_length = len(str(cell.value))
                        if cell_length > max_length:
                            max_length = cell_length
                except:
                    pass

            adjusted_width = max(min(max_length + 2, max_width), min_width)
            ws.column_dimensions[column_letter].width = adjusted_width

    def _add_title_row(self, ws, title, row=1, cols=5):
        """Добавляет строку-заголовок"""
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=cols)
        cell = ws.cell(row=row, column=1, value=title)
        cell.font = Font(bold=True, size=14)
        cell.alignment = Alignment(horizontal="center")
        cell.fill = self.title_fill
        return row + 1

    def add_formulas_sheet(self, formulas):
        """Лист 1: Все формулы"""
        ws = self.wb.create_sheet("Формулы")

        # Заголовок
        row = self._add_title_row(ws, "Справочник формул", 1, 7)
        ws.cell(row=row, column=1, value=f"Экспортировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        row += 2

        # Заголовки таблицы
        headers = ["№", "Символ", "Название", "Тип", "Выражение", "Ед.изм.", "Категория"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            self._apply_header_style(cell)
        row += 1

        # Данные
        for idx, formula in enumerate(formulas, 1):
            data = [
                idx,
                formula.symbol,
                formula.name,
                "Входной" if formula.is_input else "Вычисляемая",
                formula.expression if not formula.is_input else f"(по умолч: {formula.default_value or '—'})",
                formula.unit or "—",
                formula.category.name if formula.category else "—"
            ]

            for col, value in enumerate(data, 1):
                cell = ws.cell(row=row, column=col, value=value)
                self._apply_cell_style(cell, is_number=(col == 1), is_input=formula.is_input)
            row += 1

        # Легенда
        row += 1
        ws.cell(row=row, column=1, value="Легенда:").font = Font(italic=True)
        row += 1
        cell = ws.cell(row=row, column=1, value="  ■ Входной параметр")
        cell.fill = self.input_fill
        row += 1
        cell = ws.cell(row=row, column=1, value="  ■ Вычисляемая формула")
        cell.fill = self.calc_fill

        self._auto_width(ws)
        return self

    def add_calculation_sheet(self, results, input_values, formula_map):
        """Лист 2: Результаты вычислений"""
        ws = self.wb.create_sheet("Результаты расчёта")

        # Заголовок
        row = self._add_title_row(ws, "Результаты вычислений", 1, 5)
        ws.cell(row=row, column=1, value=f"Дата расчёта: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        row += 2

        # Заголовки
        headers = ["Символ", "Название", "Формула", "Результат", "Ед.изм."]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            self._apply_header_style(cell)
        row += 1

        # Входные параметры
        ws.cell(row=row, column=1, value="ВХОДНЫЕ ПАРАМЕТРЫ").font = Font(bold=True, color="FFFFFF")
        ws.cell(row=row, column=1).fill = PatternFill(start_color="28a745", fill_type="solid")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
        row += 1

        for symbol, value in input_values.items():
            formula = formula_map.get(symbol)
            data = [
                symbol,
                formula.name if formula else "",
                "(введено)",
                round(value, 4) if isinstance(value, float) else value,
                formula.unit if formula else ""
            ]
            for col, val in enumerate(data, 1):
                cell = ws.cell(row=row, column=col, value=val)
                self._apply_cell_style(cell, is_number=(col == 4), is_input=True)
            row += 1

        # Вычисленные
        row += 1
        ws.cell(row=row, column=1, value="ВЫЧИСЛЕННЫЕ ЗНАЧЕНИЯ").font = Font(bold=True, color="FFFFFF")
        ws.cell(row=row, column=1).fill = PatternFill(start_color="ffc107", fill_type="solid")
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
        row += 1

        for symbol, result in results.items():
            if symbol not in input_values and result.success:
                formula = formula_map.get(symbol)
                data = [
                    symbol,
                    formula.name if formula else "",
                    result.formula_expression or "",
                    round(result.value, 4) if result.value else "—",
                    formula.unit if formula else ""
                ]
                for col, val in enumerate(data, 1):
                    cell = ws.cell(row=row, column=col, value=val)
                    self._apply_cell_style(cell, is_number=(col == 4), is_input=False)
                row += 1

        self._auto_width(ws)
        return self

    def add_variants_summary_sheet(self, project, variants):
        """Лист 3: Сводная таблица всех вариантов"""
        ws = self.wb.create_sheet("Сводная таблица")

        if not variants:
            ws.cell(row=1, column=1, value="Нет вариантов")
            return self

        # Заголовок
        row = self._add_title_row(ws, f"Проект: {project.name}", 1, 10)
        ws.cell(row=row, column=1, value=f"Всего вариантов: {len(variants)}")
        ws.cell(row=row, column=3, value=f"Экспорт: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        row += 2

        # Собираем все символы
        from .models import Formula
        all_symbols = set()
        for variant in variants:
            for vv in variant.values.all():
                all_symbols.add(vv.formula.symbol)

        # Сортируем: входные → вычисляемые
        formulas = Formula.objects.filter(symbol__in=all_symbols).order_by('-is_input', 'symbol')
        symbols_order = [(f.symbol, f.is_input, f.name) for f in formulas]

        # Заголовки
        headers = ["№ варианта", "Студент"] + [s[0] for s in symbols_order]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            self._apply_header_style(cell)

            # Подсветка входных/вычисляемых
            if col > 2:
                is_input = symbols_order[col - 3][1]
                if is_input:
                    cell.fill = PatternFill(start_color="28a745", fill_type="solid")
                else:
                    cell.fill = PatternFill(start_color="ffc107", fill_type="solid")

        # Названия формул (вторая строка заголовка)
        row += 1
        ws.cell(row=row, column=1, value="")
        ws.cell(row=row, column=2, value="")
        for col, (symbol, is_input, name) in enumerate(symbols_order, 3):
            cell = ws.cell(row=row, column=col, value=name[:20])
            cell.font = Font(italic=True, size=9)
            cell.alignment = self.center_alignment

        row += 1

        # Данные вариантов
        for variant in variants:
            ws.cell(row=row, column=1, value=variant.number).alignment = self.center_alignment
            ws.cell(row=row, column=2, value=variant.student_name or "—")

            values_dict = {vv.formula.symbol: vv.value for vv in variant.values.all()}

            for col, (symbol, is_input, _) in enumerate(symbols_order, 3):
                value = values_dict.get(symbol)
                cell = ws.cell(row=row, column=col, value=round(value, 4) if value else "—")
                self._apply_cell_style(cell, is_number=True, is_input=is_input)

            row += 1

        # Статистика
        row += 2
        ws.cell(row=row, column=1, value="Статистика:").font = Font(bold=True)
        row += 1

        for col, (symbol, is_input, name) in enumerate(symbols_order, 3):
            values = []
            for variant in variants:
                for vv in variant.values.all():
                    if vv.formula.symbol == symbol and vv.value is not None:
                        values.append(vv.value)

            if values:
                ws.cell(row=row, column=col, value=f"мин: {min(values):.2f}")
                ws.cell(row=row + 1, column=col, value=f"макс: {max(values):.2f}")
                ws.cell(row=row + 2, column=col, value=f"сред: {sum(values) / len(values):.2f}")

        self._auto_width(ws, min_width=12)
        return self

    def add_formulas_reference_sheet(self, formulas):
        """Лист 4: Справочник формул (краткий)"""
        ws = self.wb.create_sheet("Справочник")

        row = self._add_title_row(ws, "Используемые формулы", 1, 3)
        row += 1

        headers = ["Символ", "Выражение", "Описание"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            self._apply_header_style(cell)
        row += 1

        for formula in formulas:
            if not formula.is_input:
                data = [
                    formula.symbol,
                    formula.expression,
                    f"{formula.name} [{formula.unit}]" if formula.unit else formula.name
                ]
                for col, val in enumerate(data, 1):
                    ws.cell(row=row, column=col, value=val)
                row += 1

        self._auto_width(ws)
        return self

    def get_file(self):
        """Возвращает файл как bytes"""
        output = io.BytesIO()
        self.wb.save(output)
        output.seek(0)
        return output.getvalue()


def export_full_data(formulas=None, calculation_results=None, input_values=None,
                     project=None, variants=None, formula_map=None):
    """
    Универсальная функция экспорта всех данных в один файл Excel

    Args:
        formulas: Список всех формул
        calculation_results: Результаты текущего расчёта
        input_values: Входные значения текущего расчёта
        project: Проект (для вариантов)
        variants: Список вариантов
        formula_map: Словарь формул {symbol: Formula}
    """
    exporter = ExcelExporter()

    # Лист 1: Все формулы (всегда)
    if formulas:
        exporter.add_formulas_sheet(formulas)

    # Лист 2: Результаты расчёта (если есть)
    if calculation_results and input_values and formula_map:
        exporter.add_calculation_sheet(calculation_results, input_values, formula_map)

    # Лист 3: Сводная таблица вариантов (если есть)
    if project and variants:
        exporter.add_variants_summary_sheet(project, variants)

        # Лист 4: Справочник формул
        if formulas:
            exporter.add_formulas_reference_sheet(formulas)

    return exporter.get_file()