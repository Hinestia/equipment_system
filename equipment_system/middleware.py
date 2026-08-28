"""
Требует вход в систему для всех страниц, кроме явных исключений.
/admin/ в исключения не входит формально, но она и так защищена собственной
системой входа Django — пользователь просто увидит форму входа Django admin
вместо нашей, если попробует зайти туда напрямую без сессии.
"""
from django.conf import settings
from django.contrib.auth.views import redirect_to_login

# Пути, доступные без входа в систему. Указываются как префиксы.
# Медиафайлы (сгенерированные документы) сюда намеренно не входят — их скачивание
# тоже требует входа, иначе прямая ссылка на файл работала бы в обход авторизации.
EXEMPT_PATH_PREFIXES = (
    '/accounts/login/',
    '/static/',
)


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        is_exempt = path.startswith(EXEMPT_PATH_PREFIXES) or path.startswith('/admin/')
        if not is_exempt and not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url=settings.LOGIN_URL)
        return self.get_response(request)
