from django.apps import AppConfig


class FormulasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'formulas'
    verbose_name = 'Формулы'

    def ready(self):
        # Импортируем сигналы при загрузке приложения
        import formulas.signals  # noqa