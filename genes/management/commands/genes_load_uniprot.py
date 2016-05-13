# The docstring in this module is written in rst format so that it can be
# collected by sphinx and integrated into django-genes/README.rst file.

"""
   This command can be used to populate database with UniProtKB
   identifiers. It takes one argument:

   * uniprot_file: location of a file mapping UniProtKB IDs to Entrez
     and Ensembl IDs

   **Important:** Before calling this command, please make sure that
   both Ensembl and Entrez identifiers have been loaded into the
   database.

   After downloading the gzipped file, use ``zgrep`` command to get
   the lines we need (the original file is quite large), then run this
   command:

   ::

      wget -P data/ -N ftp://ftp.uniprot.org/pub/databases/uniprot/\
current_release/knowledgebase/idmapping/idmapping.dat.gz
      zgrep -e "GeneID" -e "Ensembl" data/idmapping.dat.gz \
> data/uniprot_entrez_ensembl.txt
      python manage.py genes_load_uniprot \
--uniprot_file=data/uniprot_entrez_ensembl.txt
"""

import logging
import sys
from optparse import make_option

from django.core.management.base import BaseCommand
from genes.models import CrossRefDB, CrossRef, Gene

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--uniprot_file', action='store', dest='uniprot',
                    help='filtered uniprot file (i.e. with: zgrep "GeneID" '
                    'idmapping.dat.gz > uniprot_entrez.txt'),
    )

    help = 'Add UniProtKB cross references.'

    def handle(self, *args, **options):
        uniprot_file = options.get('uniprot')
        if uniprot_file:
            uniprot_file = open(uniprot_file)
        if uniprot_file:
            entrez_set = set(Gene.objects.all().values_list('entrezid',
                                                            flat=True))
            uniprot_entrez = {}
            for line in uniprot_file:
                (uniprot_id, junk, entrez_id) = line.strip().split()
                entrez_id = int(entrez_id)
                if entrez_id in entrez_set:
                    uniprot_entrez[uniprot_id] = entrez_id
            uniprot = CrossRefDB.objects.get(name='UniProtKB')
            for uniprot_id in uniprot_entrez.keys():
                gene = Gene.objects.get(entrezid=uniprot_entrez[uniprot_id])
                try:
                    uniprot_xr = CrossRef.objects.get(crossrefdb=uniprot,
                                                      xrid=uniprot_id)
                    uniprot_xr.gene = gene
                    uniprot_xr.save()
                except CrossRef.DoesNotExist:
                    uniprot_xr = CrossRef(crossrefdb=uniprot, xrid=uniprot_id,
                                          gene=gene)
                    uniprot_xr.save()
            uniprot_file.close()
        else:
            logger.error("Couldn\'t load uniprot %s", options.get('uniprot'),
                         exc_info=sys.exc_info(), extra={'options': options})
