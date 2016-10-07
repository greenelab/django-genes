from django.conf.urls import url
from haystack.query import SearchQuerySet

from genes.models import Gene, CrossRefDB, CrossRef
from genes.utils import translate_genes
from organisms.api import OrganismResource

# Import and set logger
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

try:
    from tastypie import fields
    from tastypie.resources import ModelResource, ALL, ALL_WITH_RELATIONS
    from tastypie.utils import trailing_slash

except ImportError:
    logger.info('Not using django-tastypie in genes/api.py file')
    quit()

GENE_RESULT_LIMIT = 15


class GeneResource(ModelResource):
    entrezid = fields.IntegerField(attribute='entrezid')
    pk = fields.IntegerField(attribute='id')
    xrids = fields.ToManyField('genes.api.CrossRefResource',
                               'crossref_set', related_name='gene',
                               full=True)

    class Meta:
        queryset = Gene.objects.all()
        resource_name = 'gene'
        filtering = {'entrezid': ALL, 'pk': ALL, 'symbol': ALL}
        allowed_methods = ['get']

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/search%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('get_search'), name="api_get_search"),
            url(r"^(?P<resource_name>%s)/xrid_translate%s$" %
                (self._meta.resource_name, trailing_slash()),
                self.wrap_view('translate_gene_ids'),
                name="api_translate_gene_ids"),
        ]

    def get_search(self, request, **kwargs):
        # This code uses Haystack to search for genes
        self.method_check(request, allowed=['get', 'post'])
        self.throttle_check(request)

        if request.GET.get('gene_result_limit'):
            try:
                # Make sure the input is already an integer
                # or can be coerced into one.
                gene_result_limit = int(
                    request.GET.get('gene_result_limit'))
            except ValueError:
                # Keep the gene_result_limit at whatever the
                # GENE_RESULT_LIMIT setting is set to at
                # the top of the file
                gene_result_limit = GENE_RESULT_LIMIT

        else:
            gene_result_limit = GENE_RESULT_LIMIT

        search_string = request.GET.get('query')

        organism_uri = request.GET.get('organism')
        organism = None
        if organism_uri:
            organism = OrganismResource().get_via_uri(organism_uri,
                                                      request)
        if search_string:
            search_toks = set(search_string.split())
        else:
            search_toks = []

        genes = []

        for search in search_toks:
            item = {}
            item['search'] = search
            sqs = SearchQuerySet().models(Gene)
            if organism is not None:
                sqs = sqs.filter(organism=organism)
            sqs = sqs.filter(content=search)
            sqs = sqs.load_all()[:gene_result_limit]
            objects = []

            for result in sqs:
                bundle = self.build_bundle(obj=result.object,
                                           request=request)
                bundle = self.full_dehydrate(bundle)
                objects.append(bundle)

            item['found'] = objects
            genes.append(item)

        self.log_throttled_access(request)
        return self.create_response(request, genes)

    def translate_gene_ids(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        self.throttle_check(request)

        # Extract relevant parameters
        gene_list = request.POST.getlist('gene_list')
        from_id = request.POST.get('from_id')
        to_id = request.POST.get('to_id')
        organism = request.POST.get('organism')

        # Call the translate_genes method in genes.utils to
        # do the actual translating.
        return_ids_dict = translate_genes(id_list=gene_list,
                                          from_id=from_id, to_id=to_id,
                                          organism=organism)

        return self.create_response(request, return_ids_dict)


class CrossRefDBResource(ModelResource):
    name = fields.CharField(attribute='name')
    url = fields.CharField(attribute='url')

    class Meta:
        queryset = CrossRefDB.objects.all()
        allowed_methods = ['get']
        filtering = {'name': ALL,
                     'url': ALL}


class CrossRefResource(ModelResource):
    xrid = fields.CharField(attribute='xrid')
    crossrefdb = fields.ToOneField(CrossRefDBResource, 'crossrefdb')
    gene = fields.ToOneField(GeneResource, 'gene')
    db_url = fields.CharField(attribute='specific_url')

    class Meta:
        queryset = CrossRef.objects.all()
        allowed_methods = ['get']
        filtering = {
            'xrid': ALL,
            'crossrefdb': ALL,
            'gene': ALL_WITH_RELATIONS}
