from pathlib import Path
# from decouple import config
from django.urls import reverse_lazy

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-secret-key'

DEBUG = True

LOGIN_ATTEMPTS = 50
REGISTER_ATTEMPTS = 50

LOGIN_RATE_LIMIT = f"{LOGIN_ATTEMPTS}/h"
REGISTER_RATE_LIMIT = f"{REGISTER_ATTEMPTS}/h"

ALLOWED_HOSTS = [
    '98.84.189.25'
    '184.72.118.136',
    'localhost',
    '127.0.0.1',
    '*'
]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.forms',
    'usuario',
    'terapia.apps.TerapiaConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'terapia.middleware.RateLimitMiddleware',
]

ROOT_URLCONF = 'easy_talk.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'easy_talk.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Authentication
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = "usuario.Usuario"

LOGIN_REDIRECT_URL = LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = reverse_lazy('login')

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True

# Static and media files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Other settings

FORM_RENDERER = 'easy_talk.renderers.CustomFormRenderer'
FIXTURE_DIRS = [BASE_DIR / 'fixtures']

# Email

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@easytalk.com'

# ============================
# Configuração do django-ratelimit
# ============================

def get_client_ip_for_ratelimit(request):
    """
    Retorna o IP do cliente para uso pelo django-ratelimit.

    Prioridade:
    1) HTTP_X_FORWARDED_FOR (primeiro IP da cadeia)
    2) HTTP_X_REAL_IP
    3) REMOTE_ADDR (fallback)
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        # Pode vir algo como "ip1, ip2, ip3"; pega o primeiro
        ip = forwarded_for.split(",")[0].strip()
        if ip:
            return ip

    ip = request.META.get("HTTP_X_REAL_IP")
    if ip:
        return ip

    ip = request.META.get("REMOTE_ADDR")
    if ip:
        return ip

    # Fallback defensivo: evita ImproperlyConfigured se tudo vier vazio
    return "127.0.0.1"

RATELIMIT_IP_META_KEY = get_client_ip_for_ratelimit
