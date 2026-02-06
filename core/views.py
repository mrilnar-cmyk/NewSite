from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView, UpdateView
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.urls import reverse_lazy
from django.contrib import messages

from formulas.models import Formula, Category, FormulaChart
from .forms import LoginForm, RegistrationForm, ProfileForm, CustomPasswordResetForm, CustomSetPasswordForm
from .models import User


class HomeView(View):
    """Главная страница (лендинг для неавторизованных)"""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return render(request, 'core/home.html')


class DashboardView(LoginRequiredMixin, View):
    """Рабочий стол для авторизованных пользователей"""

    def get(self, request):
        context = {
            'formula_count': Formula.objects.count(),
            'category_count': Category.objects.count(),
            'chart_count': FormulaChart.objects.count(),
            'input_count': Formula.objects.filter(is_input=True).count(),
            'calc_count': Formula.objects.filter(is_input=False).count(),
            'recent_formulas': Formula.objects.order_by('-updated_at')[:5],
        }
        return render(request, 'core/dashboard.html', context)


class LoginView(View):
    """Вход в систему"""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        form = LoginForm()
        return render(request, 'core/login.html', {'form': form})

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Запомнить меня
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)

            messages.success(request, f'Добро пожаловать, {user.get_short_name()}!')

            # Редирект на предыдущую страницу или dashboard
            next_url = request.GET.get('next', 'core:dashboard')
            return redirect(next_url)

        return render(request, 'core/login.html', {'form': form})


class RegisterView(View):
    """Регистрация"""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        form = RegistrationForm()
        return render(request, 'core/register.html', {'form': form})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешна! Добро пожаловать!')
            return redirect('core:dashboard')
        return render(request, 'core/register.html', {'form': form})


class LogoutView(View):
    """Выход из системы"""

    def get(self, request):
        logout(request)
        messages.info(request, 'Вы вышли из системы')
        return redirect('core:home')

    def post(self, request):
        logout(request)
        return redirect('core:home')


class ProfileView(LoginRequiredMixin, View):
    """Профиль пользователя"""

    def get(self, request):
        form = ProfileForm(instance=request.user)
        return render(request, 'core/profile.html', {'form': form})

    def post(self, request):
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён')
            return redirect('core:profile')
        return render(request, 'core/profile.html', {'form': form})


# Восстановление пароля
class CustomPasswordResetView(PasswordResetView):
    template_name = 'core/password_reset.html'
    form_class = CustomPasswordResetForm
    email_template_name = 'core/password_reset_email.html'
    success_url = reverse_lazy('core:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'core/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'core/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('core:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'core/password_reset_complete.html'