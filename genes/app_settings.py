try:
    from django.conf import settings

except ImportError:
    settings = {}

GENE_RESULT_LIMIT = getattr(settings, 'GENE_RESULT_LIMIT', 15)
