"""
Base settings for wordduel_backend project.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from Backend/.env (if present).
load_dotenv(BASE_DIR / ".env", override=False)

# SECURITY WARNING: keep the secret key used in production secret!
def env(name: str, default=None, cast=None):
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default

    if cast is None:
        return raw

    try:
        return cast(raw)
    except (TypeError, ValueError):
        return default


def env_required(name: str, cast=None):
    raw = os.getenv(name)
    if raw is None or raw == "":
        raise RuntimeError(f"Missing required environment variable: {name}")

    if cast is None:
        return raw

    return cast(raw)


def env_csv(name: str, default: str) -> list[str]:
    raw = env(name, default=default)
    if not raw:
        return []
    return [item.strip() for item in str(raw).split(",") if item.strip()]


SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
def env_bool(name: str, default: bool) -> bool:
    raw = env(name, default=None)
    if raw is None or raw == "":
        return default

    value = str(raw).strip().lower()
    if value in {"1", "true", "t", "yes", "y", "on", "debug", "dev"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off", "release", "prod", "production"}:
        return False
    return default


DEBUG = env_bool("DEBUG", default=True)

ALLOWED_HOSTS = env_csv("ALLOWED_HOSTS", default="localhost,127.0.0.1")

# Application definition
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'channels',
    
    'apps.accounts',
    'apps.game',
    'apps.dictionary',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
DB_ENGINE = env("DB_ENGINE", default="django.db.backends.postgresql")
if DB_ENGINE == "django.db.backends.sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": env("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": env("DB_NAME", default="wordduel"),
            "USER": env("DB_USER", default="postgres"),
            "PASSWORD": env("DB_PASSWORD", default="postgres"),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env("DB_PORT", default=5432, cast=int),
        }
    }

# Password validation
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

# Default Auto Field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.accounts.utils.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# DRF-Spectacular (Swagger) Configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'WordDuel API',
    'DESCRIPTION': 'Real-time multiplayer word guessing game API',
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVE_AUTHENTICATION': None,
    'TAGS_SORTER': 'alpha',
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = env_csv(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
)

# Channels Configuration
#
# Default to in-memory so the backend runs without Redis for local/dev usage.
# Set USE_REDIS=true in the environment to enable Redis-backed channel layers.
USE_REDIS = env_bool("USE_REDIS", default=False)
if USE_REDIS:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [
                    (
                        env("REDIS_HOST", default="localhost"),
                        env("REDIS_PORT", default=6379, cast=int),
                    )
                ],
            },
        },
    }
else:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# JWT Configuration
JWT_SECRET = env('JWT_SECRET', default='your-jwt-secret-key')
JWT_ALGORITHM = env('JWT_ALGORITHM', default='HS256')
JWT_EXPIRATION_HOURS = env('JWT_EXPIRATION_HOURS', default=24, cast=int)

# Game Settings
WORDDUEL_MAX_ROUNDS = env('WORDDUEL_MAX_ROUNDS', default=5, cast=int)
WORDDUEL_TICK_DURATION_MS = env('WORDDUEL_TICK_DURATION_MS', default=5000, cast=int)
MATCHMAKING_TIMEOUT_SECONDS = env('MATCHMAKING_TIMEOUT_SECONDS', default=10, cast=int)
