# -*- coding: utf-8 -*-
"""
Django settings for invoicing project.

Generated by 'django-admin startproject' using Django 1.8.19.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'yf2+1q47m@7n7zh&#^f*stowz!g(y#b5o#-!z7a-x75(a36#iy'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'invoicing_app',
    'autofixture',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

EVENTBRITE_TAX_INFORMATION = {
    'BR': {
        'tax_identifier_type': 'CNPJ',
        'tax_identifier_number': '15.913.672/0001-65',
        'supplier_name': u'EVENTIOZ GESTÃO DE EVENTOS ONLINE LTDA',
        'supplier_address': u'Alameda Jau',
        'supplier_address_2': u'48 - 13 andar',
        'supplier_postal_code': u'01420-00',
        'supplier_city': u'Jardins São Paulo',
        'supplier_region': u'SP',
    },
    'AR': {
        'tax_identifier_type': 'CUIT',
        'tax_identifier_number': '30710388764',
        'supplier_name': u'Eventbrite Argentina S.A.',
        'supplier_address': u'República del Líbano 981',
        'supplier_address_2': '',
        'supplier_postal_code': u'5501',
        'supplier_city': u'Godoy Cruz',
        'supplier_region': u'Mendoza',
    }
}

ROOT_URLCONF = 'invoicing.urls'

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

WSGI_APPLICATION = 'invoicing.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'invoicing',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': 'localhost',
        'PORT': 3306,
    },
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
