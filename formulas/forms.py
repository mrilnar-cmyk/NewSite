from django import forms
from .models import Category, Formula, FormulaVariable


class CategoryForm(forms.ModelForm):
    """Форма для категории"""

    class Meta:
        model = Category
        fields = ['name', 'description', 'parent', 'order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название категории'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Описание (необязательно)'
            }),
            'parent': forms.Select(attrs={
                'class': 'form-select'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Исключаем саму себя и своих потомков из списка родителей
        if self.instance and self.instance.pk:
            # Получаем всех потомков рекурсивно
            descendants = self._get_descendants(self.instance)
            descendants.add(self.instance.pk)

            self.fields['parent'].queryset = Category.objects.exclude(
                pk__in=descendants
            )

    def _get_descendants(self, category):
        """Рекурсивно получает все подкатегории"""
        descendants = set()
        for child in category.children.all():
            descendants.add(child.pk)
            descendants.update(self._get_descendants(child))
        return descendants

    def clean_parent(self):
        parent = self.cleaned_data.get('parent')

        # Проверка: нельзя быть родителем самому себе
        if parent and self.instance and self.instance.pk:
            if parent.pk == self.instance.pk:
                raise forms.ValidationError('Категория не может быть родителем самой себе')

            # Проверка: родитель не должен быть потомком
            descendants = self._get_descendants(self.instance)
            if parent.pk in descendants:
                raise forms.ValidationError('Нельзя выбрать подкатегорию в качестве родителя')

        return parent

class FormulaForm(forms.ModelForm):
    """Форма для формулы"""

    class Meta:
        model = Formula
        fields = [
            'symbol', 'name', 'expression', 'unit',
            'description', 'category', 'order', 'is_input', 'default_value'
        ]
        widgets = {
            'symbol': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: K, Re, alpha1'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Понятное название'
            }),
            'expression': forms.Textarea(attrs={
                'class': 'form-control font-monospace',
                'rows': 3,
                'placeholder': 'Например: R1 * (1 - cos(alpha))',
                'id': 'expression-input'
            }),
            'unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'м, кг, Вт/(м²·К)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Описание и пояснения'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'is_input': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'default_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any',
                'placeholder': 'Значение по умолчанию'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем expression необязательным (будет проверяться в clean)
        self.fields['expression'].required = False
        self.fields['category'].required = False
        self.fields['unit'].required = False
        self.fields['description'].required = False
        self.fields['default_value'].required = False

    def clean(self):
        cleaned_data = super().clean()
        is_input = cleaned_data.get('is_input', False)
        expression = cleaned_data.get('expression', '').strip()

        # Если это НЕ входной параметр, то выражение обязательно
        if not is_input and not expression:
            self.add_error('expression', 'Введите выражение формулы или отметьте "Это входной параметр"')

        return cleaned_data