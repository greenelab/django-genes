# The docstring in this module is written in rst format so that it can be
# collected by sphinx and integrated into django-genes/README.rst file.

"""
   This command adds cross-reference databases for genes. It **must**
   be called for every new cross-reference database to populate the
   gene and cross-reference objects in the database. It requires 2
   arguments:

   * name: the name of the database

   * URL: the URL for that database, with the string '_REPL_' added at the
     end of the URL

   For example, this command adds Ensembl as a cross-reference
   database:

   ::

      python manage.py genes_add_xrdb --name=Ensembl \
--URL=http://www.ensembl.org/Gene/Summary?g=_REPL_

   And this command adds MIM as a cross-reference database:

   ::

      python manage.py genes_add_xrdb --name=MIM \
--URL=http://www.ncbi.nlm.nih.gov/omim/_REPL_
"""

import logging
from optparse import make_option

from django.core.management.base import BaseCommand
from genes.models import CrossRefDB

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--name', action='store', dest='name'),
        make_option('--URL', action='store', dest='url'),
    )

    help = 'Add a cross reference database if one with the provided name '\
           'does not exist, or update the URL if it does.'

    def handle(self, *args, **options):
        name = options.get('name', None)
        url = options.get('url', None)
        try:
            xrdb = CrossRefDB.objects.get(name=name)
            if xrdb.url != url:
                xrdb.url = url
                xrdb.save()
        except CrossRefDB.DoesNotExist:
            xrdb = CrossRefDB(name=name, url=url)
            xrdb.save()
