=====
Genes
=====

Genes is a Django app to represent genes.

Download and Install
--------------------
This package is registered as ``django-genes`` in PyPI and is pip installable:

.. code-block:: shell

  pip install django-genes

If any of the following dependency packages are not found on your system,
``pip`` will install them too:

* ``django 1.8 or later`` (Django web framework)

* ``django-organisms`` (``Organisms`` model, which is required by ``Genes`` model)

* ``django-haystack`` (see ``Search Indexes and Data Template`` section.)

* ``django-fixtureless`` (for unittest, see ``tests.py``)


Quick Start
-----------

1. Add **'genes'** and **'organisms'** to your ``INSTALLED_APPS`` setting like this::

    INSTALLED_APPS = (
        ...
        'organisms',
        'genes',

    )


2. Run ``python manage.py migrate`` command to create ``genes`` and ``organisms``
   models.


Search Indexes and Data Template
--------------------------------

The module ``search_indexes.py`` can be used by **django haystack**
(https://github.com/django-haystack/django-haystack) to search genes.
It includes the Gene fields that should be included in the search index, and how
they should be weighted. The ``text`` field refers to a document that is built
for the search engine to index. The location of data template for this document
is:
``genes/templates/search/indexes/gene_text.txt``.

For more information, see:
http://django-haystack.readthedocs.org/en/latest/tutorial.html#handling-data


Usage of Management Commands
----------------------------

This app includes four management commands in ``management/commands/``
sub-directory to populate the database:

1. **genes_add_xrdb**

  This command adds cross-reference databases for genes. It **must** be called
  for every new cross-reference database to populate the gene and
  cross-reference objects in the database. It takes 2 arguments:

  * The name of the database
  * The URL for that database, with the string '_REPL_' added at the end of the URL

  For example, this command adds Ensembl as a cross-reference database:

  .. code-block:: shell

    python manage.py genes_add_xrdb --name=Ensembl --URL=http://www.ensembl.org/Gene/Summary?g=_REPL_

  And this command adds MIM as a cross-reference database:

  .. code-block:: shell

    python manage.py genes_add_xrdb --name=MIM --URL=http://www.ncbi.nlm.nih.gov/omim/_REPL_


2. **genes_load_geneinfo**

  This command parses gene info file(s) and saves the corresponding gene
  objects into the database. It takes 4 arguments:

  * Location of gene info file
  * Taxonomy ID for organism for which genes are being populated
  * Systematic column in gene info file
  * Symbol column in gene info file

  The following example shows how to download a gzipped human gene info file
  from NIH FTP server, and populate the database based on this file.

  .. code-block:: shell

    # Create a temporary data directory:
    mkdir data

    # Download a gzipped human gene info file into data directory:
    wget -P data/ -N   ftp://ftp.ncbi.nih.gov/gene/DATA/GENE_INFO/Mammalia/Homo_sapiens.gene_info.gz

    # Unzip downloaded file:
    gunzip -c data/Homo_sapiens.gene_info.gz > data/Homo_sapiens.gene_info

    # Call genes_load_geneinfo to populate the database:
    python manage.py genes_load_geneinfo --geneinfo_file=data/Homo_sapiens.gene_info --taxonomy_id=9606 --systematic_col=2 --symbol_col=2


3. **genes_load_uniprot.py**

  This command can be used to populate database with UniProtKB identifiers.
  It takes one argument:

  * The location of a file mapping UniProtKB IDs to Entrez and Ensembl IDs

  **Important:** Before calling this command, please make sure that both
  Ensembl and Entrez identifiers have been loaded into the database.

  After downloading the gzipped file, use ``zgrep`` command to get the lines we
  need (the original file is quite large), then run this command:

  .. code-block:: shell

    wget -P data/ -N  ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/idmapping/idmapping.dat.gz
    zgrep -e "GeneID" -e "Ensembl" data/idmapping.dat.gz > data/uniprot_entrez_ensembl.txt
    python manage.py genes_load_uniprot --uniprot_file=data/uniprot_entrez_ensembl.txt


4. **genes_load_wb.py**

  This command can be used to populate database with WormBase identifiers.
  It takes 3 arguments:

  * The URL of wormbase xrefs file
  * The name of the cross-reference database (which defaults to 'WormBase')
  * The Taxonomy ID assigned to this organism by NCBI

  As is expected, the WormBase cross-reference database should be populated
  using the ``genes_add_xrdb`` command (see command #1) before running this command
  to populate the WormBase identifiers. Here is an example:

  .. code-block:: shell

    # Find latest version of WormBase here:
    # http://www.wormbase.org/about/release_schedule#102--10-1
    python manage.py genes_load_wb --wb_url=ftp://ftp.wormbase.org/pub/wormbase/releases/WS243/species/c_elegans/PRJNA13758/c_elegans.PRJNA13758.WS243.xrefs.txt.gz --taxonomy_id=6239
