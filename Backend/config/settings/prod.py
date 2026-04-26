"""
Production settings for wordduel_backend project.
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Database
DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': env_required('DB_NAME'),
        'USER': env_required('DB_USER'),
        'PASSWORD': env_required('DB_PASSWORD'),
        'HOST': env_required('DB_HOST'),
        'PORT': env('DB_PORT', default=5432, cast=int),
    }
}

# CORS Configuration for production
CORS_ALLOWED_ORIGINS = env_csv('CORS_ALLOWED_ORIGINS', default='https://yourdomain.com')

# Channels: use Redis in production
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                (env("REDIS_HOST", default="localhost"), env("REDIS_PORT", default=6379, cast=int))
            ],
        },
    },
}

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
}
