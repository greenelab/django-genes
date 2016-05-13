#!/usr/bin/env python

# The docstring in this module is written in rst format so that it can be
# collected by sphinx and integrated into django-genes/README.rst file.

"""
   This management command will read an input gene history file and
   find all genes whose tax_id match input taxonomy ID. If the gene
   already exists in the database, the Gene record in database will be
   set as obsolete; if not, a new obsolete Gene record will be created
   in the database.

   The command accepts 2 required arguments and 3 optional arguments:

   * (Required) gene_history_file: Input gene history file. A gzipped
     example file can be found at:
     ftp://ftp.ncbi.nih.gov/gene/DATA/gene_history.gz

   * (Required) tax_id: Taxonomy ID assigned by NCBI to a certain
     organism. Genes of the other organisms in input file will be
     skipped.

   * (Optional) tax_id_col: column number of tax_id in input file.
     Default is 1.

   * (Optional) discontinued_id_col: column number of discontinued
     GeneID in input file. Default is 3.

   * (Optional) discontinued_symbol_col: column number of gene's
     discontinued symbol in input file. Default is 4.

   Note that column numbers in the last three arguments all start from
   1, **not** 0.

   For example, to add obsolete genes whose tax_id is 208964 in the
   file "gene_history", we will use the command like this:

   ::

      # Download file into your data directory:
      cd /data_dir; wget ftp://ftp.ncbi.nih.gov/gene/DATA/gene_history.gz

      # Unzip the downloaded file into "gene_history"
      gunzip gene_history.gz

      # Run management command:
      python manage.py genes_load_gene_history /data_dir/gene_history 208964 \
--tax_id_col=1 --discontinued_id_col=3 --discontinued_symbol_col=4

   (Here ``--tax_id_col=1 --discontinued_id_col=3
   --discontinued_symbol_col=4`` are optional because they are using
   default values.)
"""


from django.core.management.base import BaseCommand, CommandError
from organisms.models import Organism
from genes.models import Gene


class Command(BaseCommand):
    help = ('Read input gene_history file and set or create obsolete Gene '
            'records in the database.')

    def add_arguments(self, parser):
        parser.add_argument('gene_history_file', type=file)
        parser.add_argument('tax_id', type=str)
        parser.add_argument('--tax_id_col', type=int, default=1,
                            dest='tax_id_col',
                            help='column number of tax_id')
        parser.add_argument('--discontinued_id_col', type=int, default=3,
                            dest='id_col',
                            help='column number of Discontinued_GeneID')
        parser.add_argument('--discontinued_symbol_col', type=int, default=4,
                            dest='symbol_col',
                            help='column number of Discontinued_Symbol')

    def handle(self, *args, **options):
        try:
            import_gene_history(options['gene_history_file'],
                                options['tax_id'],
                                options['tax_id_col'] - 1,
                                options['id_col'] - 1,
                                options['symbol_col'] - 1)
            self.stdout.write(self.style.NOTICE(
                'Gene history data import succeeded'))
        except Exception as e:
            raise CommandError(
                'Data import encountered an error: import_gene_history throws '
                'an exception:\n%s' % e)


def chk_col_numbers(line_num, num_cols, tax_id_col, id_col, symbol_col):
    """
    Check that none of the input column numbers is out of range.
    (Instead of defining this function, we could depend on Python's built-in
    IndexError exception for this issue, but the IndexError exception wouldn't
    include line number information, which is helpful for users to find exactly
    which line is the culprit.)
    """

    bad_col = ''
    if tax_id_col >= num_cols:
        bad_col = 'tax_id_col'
    elif id_col >= num_cols:
        bad_col = 'discontinued_id_col'
    elif symbol_col >= num_cols:
        bad_col = 'discontinued_symbol_col'

    if bad_col:
        raise Exception(
            'Input file line #%d: column number of %s is out of range' %
            (line_num, bad_col))


def import_gene_history(file_handle, tax_id, tax_id_col, id_col, symbol_col):
    """
    Read input gene history file into the database.
    Note that the arguments tax_id_col, id_col and symbol_col have been
    converted into 0-based column indexes.
    """

    # Make sure that tax_id is not "" or "  "
    if not tax_id or tax_id.isspace():
        raise Exception("Input tax_id is blank")

    # Make sure that tax_id exists in Organism table in the database.
    try:
        organism = Organism.objects.get(taxonomy_id=tax_id)
    except Organism.DoesNotExist:
        raise Exception('Input tax_id %s does NOT exist in Organism table. '
                        'Please add it into Organism table first.' % tax_id)

    if tax_id_col < 0 or id_col < 0 or symbol_col < 0:
        raise Exception(
            'tax_id_col, id_col and symbol_col must be positive integers')

    for line_index, line in enumerate(file_handle):
        if line.startswith('#'):  # Skip comment lines.
            continue

        fields = line.rstrip().split('\t')
        # Check input column numbers.
        chk_col_numbers(line_index + 1, len(fields), tax_id_col, id_col,
                        symbol_col)

        # Skip lines whose tax_id's do not match input tax_id.
        if tax_id != fields[tax_id_col]:
            continue

        entrez_id = fields[id_col]
        # If the gene already exists in database, set its "obsolete" attribute
        # to True; otherwise create a new obsolete Gene record in database.
        try:
            gene = Gene.objects.get(entrezid=entrez_id)
            if not gene.obsolete:
                gene.obsolete = True
                gene.save()
        except Gene.DoesNotExist:
            Gene.objects.create(entrezid=entrez_id, organism=organism,
                                systematic_name=fields[symbol_col],
                                obsolete=True)
