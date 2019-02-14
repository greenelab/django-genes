# The docstring in this module is written in rst format so that it can be
# collected by sphinx and integrated into django-genes/README.rst file.

"""
   This command can be used to populate database with WormBase
   identifiers. It takes 3 arguments:

   * (Required) wb_url: URL of wormbase xrefs file;

   * (Optional) db_name: the name of the cross-reference database,
     default is 'WormBase'.

   As is expected, the WormBase cross-reference database should be
   populated using the ``genes_add_xrdb`` command (see command #1)
   before this command to populate the WormBase identifiers.
   Here is an example:

   ::

      # Find latest version of WormBase here:
      # http://www.wormbase.org/about/release_schedule#102--10-1
      python manage.py genes_load_wb --wb_url=ftp://ftp.wormbase.org/pub/\
wormbase/releases/WS243/species/c_elegans/PRJNA13758/c_elegans.PRJNA13758.WS243.xrefs.txt.gz
"""

import logging
import urllib2
import gzip
from StringIO import StringIO
from django.core.management.base import BaseCommand, CommandError
from genes.models import Gene, CrossRefDB, CrossRef

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Command(BaseCommand):
    help = 'Add wormbase identifiers to database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--wb_url',
            dest='wburl',
            required=True,
            help="URL of wormbase xrefs file."
        )
        parser.add_argument(
            '--db_name',
            dest='dbname',
            default="WormBase",
            help="Name of the database, defaults to 'WormBase'."
        )

    def handle(self, *args, **options):
        database = CrossRefDB.objects.get(name=options.get('dbname'))
        wb_url = options.get('wburl')

        xrefs_gzip_fh = gzip.GzipFile(fileobj=StringIO(
            urllib2.urlopen(wb_url, timeout=5).read()))

        for line in xrefs_gzip_fh:
            toks = line.strip().split('\t')
            systematic = 'CELE_' + toks[0]
            wbid = toks[1]
            try:
                gene = Gene.objects.get(systematic_name=systematic)
            except Gene.DoesNotExist:
                logger.info("Unable to find gene %s.", systematic)
                continue
            wb = None
            try:
                wb = CrossRef.objects.get(xrid=wbid, crossrefdb=database)
            except CrossRef.DoesNotExist:
                wb = CrossRef(xrid=wbid, crossrefdb=database)
            wb.gene = gene
            wb.save()

        xrefs_gzip_fh.close()
