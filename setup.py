import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# Allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-genes',
    version='0.2',
    packages=find_packages(),
    include_package_data=True,
    license='LICENSE.txt',
    description='A simple Django app to represent genes.',
    long_description=README,
    url='https://bitbucket.org/greenelab/django-genes',
    author='Greene Lab',
    author_email='team@greenelab.com',
    install_requires=[
        'django>=1.8',
        'django-organisms',
        'django-haystack',
        'django-fixtureless',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
    ],
)
