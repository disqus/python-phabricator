#!/usr/bin/env python

import os
import sys

from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))


def requirements2list(pfi_txt='requirements.txt'):
    here = os.path.dirname(os.path.realpath(__file__))
    f = open(os.path.join(here, pfi_txt), 'r')
    list_reqs = []
    for line in f.readlines():
        list_reqs.append(line.replace('\n', ''))
    return list_reqs


tests_requires = []


if sys.version_info[:2] < (2, 7):
    tests_requires.append('unittest2')


if sys.version_info[:2] <= (3, 3):
    tests_requires.append('mock')


about = {}
with open(os.path.join(here, 'phabricator', '__version__.py'), 'r') as f:
    exec(f.read(), about)


setup(
    name=about['__name__'],
    version=about['__version__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    url=about['__url__'],
    description=about['__description__'],
    license=about['__license__'],
    packages=find_packages(),
    zip_safe=False,
    test_suite=['tests.test_interfaces', 'tests.tests_structures'],
    install_requires=requirements2list(),
    tests_require=tests_requires,
    include_package_data=True,
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
)
