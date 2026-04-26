from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Расширенная модель пользователя"""

    ROLE_CHOICES = [
        ('teacher', 'Преподаватель'),
        ('assistant', 'Ассистент'),
    ]

    patronymic = models.CharField(
        'Отчество',
        max_length=150,
        blank=True
    )
    role = models.CharField(
        'Роль',
        max_length=20,
        choices=ROLE_CHOICES,
        default='teacher'
    )
    department = models.CharField(
        'Кафедра/Отдел',
        max_length=200,
        blank=True
    )
    phone = models.CharField(
        'Телефон',
        max_length=20,
        blank=True
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def get_full_name(self):
        """ФИО полностью"""
        parts = [self.last_name, self.first_name, self.patronymic]
        return ' '.join(p for p in parts if p)

    def get_short_name(self):
        """Фамилия И.О."""
        result = self.last_name
        if self.first_name:
            result += f' {self.first_name[0]}.'
        if self.patronymic:
            result += f'{self.patronymic[0]}.'
        return result