from django.conf.urls import url

from tastypie import fields
from tastypie.resources import ModelResource, ALL
from tastypie.utils import trailing_slash

from haystack.query import SearchQuerySet

from genes.models import Gene
from genes.utils import translate_genes
from organisms.api import OrganismResource


class GeneResource(ModelResource):
    entrezid = fields.IntegerField(attribute='entrezid')
    pk = fields.IntegerField(attribute='id')
    xrids = fields.ToManyField('genesets.api.resources.CrossrefResource',
                               'crossref_set', related_name='gene', full=True)

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
        self.is_authenticated(request)
        self.throttle_check(request)

        search_string = request.GET.get('query')

        organism_uri = request.GET.get('organism')
        organism = None
        if organism_uri:
            organism = OrganismResource().get_via_uri(organism_uri, request)
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
            sqs = sqs.load_all()[:15]
            objects = []

            for result in sqs:
                bundle = self.build_bundle(obj=result.object, request=request)
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
        return_ids_dict = translate_genes(id_list=gene_list, from_id=from_id,
                                          to_id=to_id, organism=organism)

        return self.create_response(request, return_ids_dict)