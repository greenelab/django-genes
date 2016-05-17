
Genes
*****

Genes is a Django app to represent genes.


Download and Install
====================

This package is registered as ``django-genes`` in PyPI and is pip
installable::

   pip install django-genes

If any of the following dependency packages are not found on your
system, ``pip`` will install them too:

* ``django 1.8 or later`` (Django web framework)

* ``django-organisms`` (``Organisms`` model, which is required by
  ``Genes`` model)

* ``django-haystack`` (see ``Search Indexes and Data Template``
  section.)

* ``django-fixtureless`` (for unittest, see ``tests.py``)


Quick Start
===========

1. Add **'genes'** and **'organisms'** to your ``INSTALLED_APPS``
setting like this::

      INSTALLED_APPS = (
          ...
          'organisms',
          'genes',
      )


2. Run ``python manage.py migrate`` command to create ``genes`` and
``organisms`` models.


Search Indexes and Data Template
================================

The module ``search_indexes.py`` can be used by **django haystack**
(https://github.com/django-haystack/django-haystack) to search genes.
It includes the Gene fields that should be included in the search
index, and how they should be weighted. The ``text`` field refers to a
document that is built for the search engine to index. The location of
data template for this document is:
``genes/templates/search/indexes/gene_text.txt``.

For more information, see:
http://django-haystack.readthedocs.org/en/latest/tutorial.html#handling-data


Usage of Management Commands
============================

This app includes five management commands in ``management/commands/``
sub-directory:


1. genes_add_xrdb
-----------------

 .. automodule:: genes_add_xrdb


2. genes_load_geneinfo
----------------------

 .. automodule:: genes_load_geneinfo


3. genes_load_uniprot.py
------------------------

 .. automodule:: genes_load_uniprot


4. genes_load_wb.py
-------------------

 .. automodule:: genes_load_wb


5. genes_load_gene_history.py
-----------------------------

 .. automodule:: genes_load_gene_history
