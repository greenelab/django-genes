try:
    from django.conf import settings
except ImportError:
    settings = {}

GENES_API_RESULT_LIMIT = getattr(settings, 'GENES_API_RESULT_LIMIT', 15)
