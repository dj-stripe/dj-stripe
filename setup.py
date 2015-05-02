#!/usr/bin/env python

import os
import sys

import djstripe

version = djstripe.__version__

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    os.system('python setup.py bdist_wheel upload')

if sys.argv[-1] == 'tag':
    print("Tagging the version on github:")
    os.system("git tag -a %s -m 'version %s'" % (version, version))
    os.system("git push --tags")
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

INSTALL_REQUIRES = [
    'django>=1.4',
    'stripe>=1.9.2',
    'django-model-utils>=1.4.0',
    'django-braces>=1.2.1',
    'jsonfield>=1.0.3'
]

# Add ordereddict to users of Python 2.6.
if sys.version > "2.6" and sys.version < "2.7":
    INSTALL_REQUIRES += ["ordereddict>=1.1"]

setup(
    name='dj-stripe',
    version=version,
    description=djstripe.__summary__,
    long_description=readme + '\n\n' + history,
    author=djstripe.__author__,
    author_email=djstripe.__email__,
    url=djstripe.__uri__,
    packages=[
        'djstripe',
    ],
    package_dir={'djstripe': 'djstripe'},
    include_package_data=True,
    install_requires=INSTALL_REQUIRES,
    license=djstripe.__license__,
    zip_safe=False,
    keywords='stripe django',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3'
    ],
)
