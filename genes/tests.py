import inspect
import string

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from django.core.exceptions import FieldError
from django.db import IntegrityError
from django.core.management import call_command
from fixtureless import Factory

import haystack
from haystack.query import SearchQuerySet
from tastypie.api import Api
from tastypie.test import ResourceTestCaseMixin

from organisms.models import Organism
from genes.models import Gene, CrossRef, CrossRefDB
from genes.utils import translate_genes
from genes.search_indexes import GeneIndex
from genes.app_settings import GENES_API_RESULT_LIMIT

factory = Factory()


# REQUIRES ELASTICSEARCH TO BE SETUP AS THE HAYSTACK PROVIDER.
TEST_INDEX = {
    'default': {
        'ENGINE': 'haystack.backends.elasticsearch_backend.'
                  'ElasticsearchSearchEngine',
        'URL': 'http://127.0.0.1:9200/',
        'TIMEOUT': 60 * 10,
        'INDEX_NAME': 'test_index',
    },
}

ROOT_URLCONF = getattr(settings, 'ROOT_URLCONF', None)


class GeneDBConstraintsTestCase(TestCase):
    """
    Checks that new Genes can be created in the database under different
    circumstances. Also checks that the exceptions we are looking for are
    raised when the Genes that are trying to be created do not comply with
    database constraints.
    """

    def test_std_and_sys_name_present(self):
        """
        Check that this throws no errors.
        """
        factory.create(Gene, {'standard_name': 'A1',
                              'systematic_name': 'a12'})

    def test_only_sys_name_present(self):
        """
        Check that this throws no errors.
        """
        factory.create(Gene, {'standard_name': None,
                              'systematic_name': 'b34'})

    def test_only_std_name_present(self):
        """
        Check that this throws an IntegrityError from the database when
        trying to create a Gene with a null value for systematic_name.
        """
        with self.assertRaises(IntegrityError):
            factory.create(Gene, {'standard_name': 'C5',
                                  'systematic_name': None})

    def test_both_names_absent(self):
        """
        Check that the Gene.save() method throws a ValueError when
        trying to create a Gene with a null value for standard_name AND
        systematic_name.
        """
        with self.assertRaises(ValueError):
            factory.create(Gene, {'standard_name': None,
                                  'systematic_name': None})

    def test_only_sys_name_blank_space(self):
        """
        Check that the Gene.save() method throws a ValueError if there
        is no standard_name and a systematic_name is passed but it is
        a blank string.
        """
        with self.assertRaises(ValueError):
            factory.create(Gene, {'standard_name': None,
                                  'systematic_name': ' '})

    def test_good_std_name_blank_sys_name(self):
        """
        Check that this throws no errors even though the systematic_name
        passed is a blank string (as in the previous test), since a
        non-blank standard_name is passed.
        """
        factory.create(Gene, {'standard_name': 'D7',
                              'systematic_name': ' '})

    def test_std_name_and_sys_name_both_blank_space(self):
        """
        Check that the Gene.save() method throws a ValueError if
        both the standard_name and systematic_name are passed but are
        blank strings.
        """
        with self.assertRaises(ValueError):
            factory.create(Gene, {'standard_name': '  ',
                                  'systematic_name': '  '})


class TranslateTestCase(TestCase):
    def setUp(self):
        org = factory.create(Organism)
        xrdb1 = CrossRefDB(name="ASDF", url="http://www.example.com")
        xrdb1.save()
        xrdb2 = CrossRefDB(name="XRDB2", url="http://www.example.com/2")
        xrdb2.save()

        # g1 and g2 have both standard and systematic names.
        g1 = Gene(entrezid=1, systematic_name="g1", standard_name="G1",
                  description="asdf", organism=org, aliases="gee1 GEE1")
        g1.save()
        g2 = Gene(entrezid=2, systematic_name="g2", standard_name="G2",
                  description="asdf", organism=org, aliases="gee2 GEE2")
        g2.save()

        xref1 = CrossRef(crossrefdb=xrdb1, gene=g1, xrid="XRID1")
        xref1.save()
        xref2 = CrossRef(crossrefdb=xrdb2, gene=g2, xrid="XRID1")
        xref2.save()
        xref3 = CrossRef(crossrefdb=xrdb1, gene=g1, xrid="XRRID1")
        xref3.save()
        xref4 = CrossRef(crossrefdb=xrdb1, gene=g2, xrid="XRID2")
        xref4.save()

        org2 = Organism(taxonomy_id=1234, common_name="Computer mouse",
                        scientific_name="Mus computurus",
                        slug="mus-computurus")
        org2.save()
        org3 = Organism(taxonomy_id=4321, common_name="Computer screen",
                        scientific_name="Monitorus computurus",
                        slug="monitorus-computurus")
        org3.save()

        # Make systematic and standard name the same for the following genes,
        # but make organisms different. Skip entrezid 3 since that is used by
        # other tests.
        g4 = Gene(entrezid=4, systematic_name="acdc", standard_name="ACDC",
                  description="asdf", organism=org2, aliases="gee4 GEE4")
        g4.save()
        g5 = Gene(entrezid=5, systematic_name="acdc", standard_name="ACDC",
                  description="asdf", organism=org3, aliases="gee5 GEE5")
        g5.save()

        # g101 has standard name, but no systematic name.
        g101 = Gene(entrezid=101, standard_name="std_101", organism=org2)
        g101.save()

        # g102 has systematic name, but no standard name.
        g102 = Gene(entrezid=102, systematic_name="sys_102", organism=org2)
        g102.save()

    def test_translate_symbol_entrez_diff_organisms(self):
        """
        translate_genes() should be able to differentiate between different
        organism genes when passed identical symbols.
        """
        # This test also confirmed that when both standard name and systematic
        # name are available, the sysmbol will be standard name.
        translation = translate_genes(id_list=['ACDC'],
                                      from_id="Symbol", to_id="Entrez",
                                      organism="Mus computurus")
        self.assertEqual(translation, {'ACDC': [4], 'not_found': []})

    def test_translate_symbol_entrez_diff_organisms2(self):
        """
        Same as previous test, but uses the other organism as input.
        """
        translation = translate_genes(id_list=['ACDC'],
                                      from_id="Symbol", to_id="Entrez",
                                      organism="Monitorus computurus")
        self.assertEqual(translation, {'ACDC': [5], 'not_found': []})

    def test_translate_entrez_entrez(self):
        """
        Test translation from entrez to entrez.
        """
        translation = translate_genes(id_list=[1, 2],
                                      from_id="Entrez", to_id="Entrez")
        self.assertEqual(translation, {1: [1, ], 2: [2, ], 'not_found': []})

    def test_translate_entrez_standard_name(self):
        """
        Test translation from entrez to standard names.
        """
        translation = translate_genes(id_list=[1, 2],
                                      from_id="Entrez",
                                      to_id="Standard name")
        self.assertEqual(translation,
                         {1: ['G1', ], 2: ['G2', ], 'not_found': []})

    def test_translate_entrez_systematic_name(self):
        """
        Test translation from entrez to systematic names.
        """
        translation = translate_genes(id_list=[1, 2],
                                      from_id="Entrez",
                                      to_id="Systematic name")
        self.assertEqual(translation,
                         {1: ['g1', ], 2: ['g2', ], 'not_found': []})

    def test_translate_entrez_xrdb(self):
        """
        Test translation from entrez to ASDF.
        """
        translation = translate_genes(id_list=[1, 2],
                                      from_id="Entrez", to_id="ASDF")
        self.assertEqual(translation, {1: ['XRID1', 'XRRID1', ],
                                       2: ['XRID2', ], 'not_found': []})

    def test_translate_xrdb_entrez(self):
        """
        Test translation from ASDF to entrez.
        """
        translation = translate_genes(id_list=['XRID1', 'XRRID1', 'XRID2'],
                                      from_id="ASDF", to_id="Entrez")
        self.assertEqual(translation, {'XRID1': [1, ], 'XRRID1': [1, ],
                                       'XRID2': [2, ], 'not_found': []})

    def test_translate_entrez_entrez_missing(self):
        """
        Test translation from entrez to entrez with a missing value.
        """
        translation = translate_genes(id_list=[1, 2, 3],
                                      from_id="Entrez", to_id="Entrez")
        self.assertEqual(translation, {1: [1, ], 2: [2, ], 'not_found': [3]})

    def test_translate_entrez_standard_name_missing(self):
        """
        Test translation from entrez to standard names with a missing value.
        """
        translation = translate_genes(id_list=[1, 2, 3],
                                      from_id="Entrez", to_id="Standard name")
        self.assertEqual(translation,
                         {1: ['G1', ], 2: ['G2', ], 'not_found': [3]})

    def test_translate_symbol_entrez(self):
        """
        Test translation from symbol to entrez when either standard name or
        systematic name is null.
        """
        # Test the gene that has standard name.
        translation = translate_genes(id_list=['std_101'],
                                      from_id="Symbol", to_id="Entrez",
                                      organism="Mus computurus")
        self.assertEqual(translation, {'std_101': [101], 'not_found': []})
        # Test the gene that does NOT have standard name.
        translation = translate_genes(id_list=['sys_102'],
                                      from_id="Symbol", to_id="Entrez",
                                      organism="Mus computurus")
        self.assertEqual(translation, {'sys_102': [102], 'not_found': []})

    def test_translate_entrez_symbol(self):
        """
        Test translation from entrez to symbol when either standard name or
        systematic name is null.
        """
        # Test the gene that has standard name.
        translation = translate_genes(id_list=[101],
                                      from_id="Entrez", to_id="Symbol",
                                      organism="Mus computurus")
        self.assertEqual(translation, {101: ['std_101'], 'not_found': []})
        # Test the gene that does NOT have standard name.
        translation = translate_genes(id_list=[102],
                                      from_id="Entrez", to_id="Symbol",
                                      organism="Mus computurus")
        self.assertEqual(translation, {102: ['sys_102'], 'not_found': []})

    def test_empty_standard_and_systematic_names(self):
        """
        Test that a ValueError exception will be raised when we try to create a
        gene whose standard and systematic names are both empty or null, or
        ONLY consist of space characters (such as space, tab, new line, etc).
        """
        org = factory.create(Organism)

        # Neither standard_name nor systematic_name is set explicitly.
        unnamed_gene = Gene(entrezid=999, organism=org)
        self.assertRaises(ValueError, unnamed_gene.save)

        # standard_name consists of only space characters.
        # systematic_name is u'' here, because it is not set explicitly, and
        # by default "null=False" for this field in the model.
        unnamed_gene = Gene(entrezid=999, standard_name="\t  \n", organism=org)
        self.assertRaises(ValueError, unnamed_gene.save)

        # Both standard_name and systematic_name are empty strings.
        unnamed_gene = Gene(entrezid=999, standard_name="", systematic_name="",
                            organism=org)
        self.assertRaises(ValueError, unnamed_gene.save)

        # Both standard_name and systematic_name consist of space characters
        # only.
        unnamed_gene = Gene(entrezid=999, standard_name="  ",
                            systematic_name="\t  \n ", organism=org)
        self.assertRaises(ValueError, unnamed_gene.save)

    def tearDown(self):
        Organism.objects.all().delete()    # Remove Organism objects.
        Gene.objects.all().delete()        # Remove Gene objects.
        CrossRef.objects.all().delete()    # Remove CrossRef objects.
        CrossRefDB.objects.all().delete()  # Remove CrossRefDB objects.


class PrepareNameLengthTestCase(TestCase):
    """
    This TestCase prepares the prepare_name_length() method in
    search_indexes.GeneIndex.
    """
    def setUp(self):

        self.g1 = factory.create(Gene, {'standard_name': 'A1',
                                        'systematic_name': 'a12'})
        self.g2 = factory.create(Gene, {'standard_name': None,
                                        'systematic_name': 'b12'})

        self.gene_index = GeneIndex()

    def test_std_and_sys_name_present(self):
        """
        Test that name_length is 2, the length of 'A1'.
        """
        name_length = self.gene_index.prepare_name_length(self.g1)
        self.assertEqual(name_length, 2)

    def test_only_sys_name_present(self):
        """
        Test that name_length is 3, the length of 'b12'.
        """
        name_length = self.gene_index.prepare_name_length(self.g2)
        self.assertEqual(name_length, 3)


# We use @override_settings here so that the tests use the TEST_INDEX
# when building/rebuilding the search indexes, and not our real Database
# search indexes.
@override_settings(HAYSTACK_CONNECTIONS=TEST_INDEX)
class BuildingGeneIndexTestCase(TestCase):
    """
    This TestCase tests the ability to build search indexes under certain
    corner cases.
    """

    def setUp(self):
        haystack.connections.reload('default')

        # As per this documented issue in Haystack,
        # https://github.com/django-haystack/django-haystack/issues/704
        # we need to call 'rebuild_index' at the beginning to get
        # consistency of data and structure. Otherwise, the
        # 'test_std_and_sys_name_present' *sometimes* yielded a None
        # result
        call_command('rebuild_index', interactive=False, verbosity=0)

    def test_factory_gene_creation(self):
        """
        Create a gene using the factory, without any specified fields.

        Call command to build search index and then try to find the gene
        using this search index.
        """
        gene = factory.create(Gene)

        call_command('update_index', interactive=False, verbosity=0)
        sqs = SearchQuerySet().models(Gene)
        sqs = sqs.filter(content=gene.systematic_name).load_all()
        self.assertEqual(sqs[0].object, gene)

    def test_std_and_sys_name_present(self):
        """
        Create a gene using the factory, but specify both standard_
        and systematic_ names.

        Call command to build search index and then try to find the gene
        using this search index.
        """
        gene = factory.create(Gene, {'standard_name': 'A1',
                                     'systematic_name': 'a12'})

        call_command('update_index', interactive=False, verbosity=0)
        sqs = SearchQuerySet().models(Gene)
        sqs = sqs.filter(content=gene.systematic_name).load_all()
        self.assertEqual(sqs[0].object, gene)

    def test_only_sys_name_present(self):
        """
        Create a gene using the factory, specify systematic_ name and
        make standard_name explicitly None.

        Call command to build search index and then try to find the gene
        using this search index.

        """
        gene = factory.create(Gene, {'standard_name': None,
                                     'systematic_name': 'b34'})

        call_command('update_index', interactive=False, verbosity=0)
        sqs = SearchQuerySet().models(Gene)
        sqs = sqs.filter(content=gene.systematic_name).load_all()
        self.assertEqual(sqs[0].object, gene)

    def test_no_description(self):
        """
        Create a gene using the factory, specify description to be an
        empty string.

        Call command to build search index and then try to find the gene
        using this search index.

        """
        gene = factory.create(Gene, {'description': ''})

        call_command('update_index', interactive=False, verbosity=0)
        sqs = SearchQuerySet().models(Gene)
        sqs = sqs.filter(content=gene.systematic_name).load_all()
        self.assertEqual(sqs[0].object, gene)

    def tearDown(self):
        call_command('clear_index', interactive=False, verbosity=0)


# We use @override_settings here so that the tests use the TEST_INDEX
# when building/rebuilding the search indexes, and not our real Database
# search indexes.
@override_settings(HAYSTACK_CONNECTIONS=TEST_INDEX)
class APIResourceTestCase(ResourceTestCaseMixin, TestCase):
    """
    Test API endpoints for retrieving and searching gene data, using both
    GET and POST requests.
    """

    def get_api_name(self):
        """
        Utility function to get the name of the tastypie REST API in
        whatever Django project is using django-genes.
        """
        if not ROOT_URLCONF:
            return None

        proj_urls = __import__(ROOT_URLCONF)
        url_members = inspect.getmembers(proj_urls.urls)

        api_name = None
        for k, v in url_members:
            if isinstance(v, Api):
                api_name = v.api_name
        return api_name

    def create_many_genes(self, organism, num_genes):
        """
        Helper function to generate a large number of genes
        """
        # Create genes:
        for i in range(num_genes):
            Gene.objects.create(entrezid=(i + 1),
                                systematic_name="sys_name #" + str(i + 1),
                                standard_name="std_name #" + str(i + 1),
                                organism=organism)

    def setUp(self):
        haystack.connections.reload('default')

        # This line is important to set up the test case!
        super(APIResourceTestCase, self).setUp()

        self.gene1 = factory.create(Gene, {'standard_name': 'A1',
                                           'systematic_name': 'a12'})
        self.gene2 = factory.create(Gene, {'standard_name': None,
                                           'systematic_name': 'b34'})

        standard_name_prefix = 'ans'
        factory.create(Gene, {'standard_name': standard_name_prefix})

        # Create 26 more gene names that start with 'ans' and then have
        # an uppercase letter appended to it.
        for letter in string.ascii_uppercase:
            factory.create(
                Gene,
                {'standard_name': standard_name_prefix + letter}
            )

        call_command('rebuild_index', interactive=False, verbosity=0)

    def test_gene_get_search(self):
        """
        Tests API gene search when searching with a GET request
        """

        api_name = self.get_api_name()
        response = self.api_client.get(
            '/api/{}/gene/search/'.format(api_name),
            data={'query': self.gene1.standard_name}
        )

        self.assertValidJSONResponse(response)

        found_results = self.deserialize(response)[0]['found']
        best_gene_result = found_results[0]

        self.assertEqual(best_gene_result['standard_name'],
                         self.gene1.standard_name)
        self.assertEqual(best_gene_result['systematic_name'],
                         self.gene1.systematic_name)

    def test_gene_post_search(self):
        """
        Tests API gene search when searching with a POST request
        """
        api_name = self.get_api_name()

        response = self.api_client.post(
            '/api/{}/gene/search/'.format(api_name),
            data={'query': self.gene2.systematic_name}
        )

        self.assertValidJSONResponse(response)

        found_results = self.deserialize(response)[0]['found']
        best_gene_result = found_results[0]

        self.assertEqual(best_gene_result['standard_name'],
                         self.gene2.standard_name)
        self.assertEqual(best_gene_result['systematic_name'],
                         self.gene2.systematic_name)

    def test_gene_list_endpt_large_post(self):
        """
        Test that we can do a big POST request to get information back
        for a lot of genes (more than are allowed through the ~4k
        character limit for GET).

        We will set the gene_num to 1100 because

        9 * 1 = 9 chars of single-digit IDs (1-9)
        90 * 2 = 180 chars of double-digit IDs (10-99)
        900 * 3 = 2700 chars of triple-digit IDs (100-999)
        101 * 4 = 404 chars of four-digit IDs (1000-1100)
        (1100 - 1) * 1 chars of delimiters (',')

        TOTAL = 9 + 180 + 2700 + 404 + 1099 = 4392 chars.

        This is based on the
        APIResourceTestCase.test_expressionvalue_big_post() test in
        https://github.com/greenelab/adage-server/blob/master/adage/analyze/tests.py
        """
        organism = factory.create(Organism)
        gene_num = 1100

        self.create_many_genes(organism, gene_num)
        gene_ids = ",".join([str(g.id) for g
                             in Gene.objects.filter(organism=organism)])

        api_name = self.get_api_name()
        resp = self.client.post('/api/{}/gene/'.format(api_name),
                                data={'pk__in': gene_ids})

        self.assertValidJSONResponse(resp)
        self.assertEqual(
            self.deserialize(resp)['meta']['total_count'],
            gene_num
        )

    def test_gene_autocomplete_search(self):
        """
        Tests API gene autocomplete search. In the setUp method, we
        created 27 genes that start with 'ans', but this should only
        return 15 results, or however many were set in the
        GENES_API_RESULT_LIMIT setting.
        """

        api_name = self.get_api_name()

        response = self.api_client.get(
            '/api/{}/gene/autocomplete/'.format(api_name),
            data={'query': 'ans'}
        )
        self.assertValidJSONResponse(response)
        found_results = self.deserialize(response)['results']
        self.assertEqual(len(found_results), GENES_API_RESULT_LIMIT)

    def tearDown(self):
        call_command('clear_index', interactive=False, verbosity=0)


class CrossRefDBTestCase(TestCase):
    def test_saving_xrdb(self):
        """
        Test that this simple CrossRefDB creation raises no errors.
        """
        factory.create(CrossRefDB, {"name": "XRDB1"})

    def test_saving_xrdb_no_name(self):
        """
        Check that CrossRefDBs in database are required to have a non-null
        name - if they do, raise IntegrityError.
        """
        with self.assertRaises(IntegrityError):
            factory.create(CrossRefDB, {"name": None})

    def test_saving_xrdb_blank_name(self):
        """
        Check that CrossRefDBs in database are required to have a name that
        is not an empty string - if they do, raise FieldError.
        """
        with self.assertRaises(FieldError):
            factory.create(CrossRefDB, {"name": ""})


class LoadCrossRefsTestCase(TestCase):

    def setUp(self):
        xrdb1 = CrossRefDB.objects.create(
            name="Ensembl", url="http://www.ensembl.org/Gene/Summary?g=_REPL_")

        CrossRefDB.objects.create(
            name="UniProtKB", url="http://www.uniprot.org/uniprot/_REPL_")

        g1 = factory.create(Gene, {'entrezid': 50810})
        g2 = factory.create(Gene)
        g3 = factory.create(Gene)
        g4 = factory.create(Gene)

        factory.create(CrossRef, {'crossrefdb': xrdb1, 'gene': g1,
                                  'xrid': 'ENSG00000166503'})
        factory.create(CrossRef, {'crossrefdb': xrdb1, 'gene': g2,
                                  'xrid': 'ENSG00000214575'})
        factory.create(CrossRef, {'crossrefdb': xrdb1, 'gene': g3,
                                  'xrid': 'ENSG00000170312'})
        factory.create(CrossRef, {'crossrefdb': xrdb1, 'gene': g4,
                                  'xrid': 'ENSG00000172053'})

    def test_load_uniprot_mgmt_command(self):
        """
        Check that genes_load_uniprot management command loads UniProtKB
        identifiers (using Entrez and Ensembl) and that it also saves those
        relationships in the database.
        """
        call_command('genes_load_uniprot',
                     uniprot='genes/test_files/test_uniprot_entrez_ensembl.txt')

        uniprot1 = CrossRef.objects.get(xrid='A0A024R216')
        self.assertEqual(uniprot1.gene.entrezid, 50810)
        e1 = CrossRef.objects.filter(
            crossrefdb__name='Ensembl').get(gene=uniprot1.gene)
        self.assertEqual(e1.xrid, 'ENSG00000166503')

        uniprot2 = CrossRef.objects.get(xrid='A0A024R214')
        e2 = CrossRef.objects.filter(
            crossrefdb__name='Ensembl').get(gene=uniprot2.gene)
        self.assertEqual(e2.xrid, 'ENSG00000214575')

        uniprot3 = CrossRef.objects.get(xrid='A0A024QZP7')
        e3 = CrossRef.objects.filter(
            crossrefdb__name='Ensembl').get(gene=uniprot3.gene)
        self.assertEqual(e3.xrid, 'ENSG00000170312')

        uniprot4 = CrossRef.objects.get(xrid='A0A0U1RQX9')
        e4 = CrossRef.objects.filter(
            crossrefdb__name='Ensembl').get(gene=uniprot4.gene)
        self.assertEqual(e4.xrid, 'ENSG00000172053')
