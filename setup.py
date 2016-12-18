#!/usr/bin/env python

import ast
import os
import sys


class MetadataFinder(ast.NodeVisitor):
    def __init__(self):
        self.version = None
        self.summary = None
        self.author = None
        self.email = None
        self.uri = None
        self.licence = None

    def visit_Assign(self, node):
        if node.targets[0].id == '__version__':
            self.version = node.value.s
        elif node.targets[0].id == '__summary__':
            self.summary = node.value.s
        elif node.targets[0].id == '__author__':
            self.author = node.value.s
        elif node.targets[0].id == '__email__':
            self.email = node.value.s
        elif node.targets[0].id == '__uri__':
            self.uri = node.value.s
        elif node.targets[0].id == '__license__':
            self.license = node.value.s


with open(os.path.join('djstripe', '__init__.py')) as open_file:
    finder = MetadataFinder()
    finder.visit(ast.parse(open_file.read()))

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload --sign')
    os.system('python setup.py bdist_wheel upload --sign')
    sys.exit()

if sys.argv[-1] == 'tag':
    print("Tagging the version on github:")
    os.system("git tag -a %s -m 'version %s'" % (finder.version, finder.version))
    os.system("git push --tags")
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

INSTALL_REQUIRES = [
    'django!=1.9,>=1.8',  # Django has a regression in 1.9, see #275
    'django-braces>=1.9.0',
    'django-model-utils>=2.5.2',
    'django-polymorphic>=1.0',
    'jsonfield>=1.0.3',
    'pytz>=2016.6.1',
    'stripe>=1.41.1',
    'tqdm>=4.8.4',
    'python-doc-inherit~=0.3.0',
    'mock-django~=0.6.10',
]

setup(
    name='dj-stripe',
    version=finder.version,
    description=finder.summary,
    long_description=readme + '\n\n' + history,
    author=finder.author,
    author_email=finder.email,
    url=finder.uri,
    packages=[
        'djstripe',
    ],
    package_dir={'djstripe': 'djstripe'},
    include_package_data=True,
    install_requires=INSTALL_REQUIRES,
    license=finder.license,
    zip_safe=False,
    keywords='stripe django',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
)
