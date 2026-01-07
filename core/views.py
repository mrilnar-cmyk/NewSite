from django.shortcuts import render, redirect
from django.views import View
from formulas.models import Formula, Category


class HomeView(View):
    """Главная страница"""

    def get(self, request):
        context = {
            'formula_count': Formula.objects.count(),
            'category_count': Category.objects.count(),
            'recent_formulas': Formula.objects.order_by('-updated_at')[:5],
            'input_formulas': Formula.objects.filter(is_input=True).count(),
            'calculated_formulas': Formula.objects.filter(is_input=False).count(),
        }
        return render(request, 'core/home.html', context)