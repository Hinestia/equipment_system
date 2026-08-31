"""
URL configuration for equipment_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from .forms import StyledAuthenticationForm, StyledPasswordChangeForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        authentication_form=StyledAuthenticationForm,
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html',
        form_class=StyledPasswordChangeForm,
        success_url='/accounts/password_change/done/',
    ), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html',
    ), name='password_change_done'),
    path('equipment/', include('equipment.urls')),
    path('history/', include('history.urls')),
    path('documents/', include('documents.urls')),
    path('reports/', include('reports.urls')),
    path('workstations/', include('workstations.urls')),
    path('', RedirectView.as_view(pattern_name='reports:dashboard', permanent=False)),
]

# Раздача сгенерированных документов (media/) — включена всегда, а не только при
# DEBUG=True. Это упрощение оправдано тем, что система работает во внутренней
# сети без выхода в интернет (см. DEPLOY.md). Если система будет доступна шире —
# лучше отдавать media/ через Nginx (тоже описано в DEPLOY.md).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
