#!/usr/bin/env python

import sys
import os

from setuptools import setup, find_packages

tests_requires = []

def requirements2list(pfi_txt='requirements.txt'):
    here = os.path.dirname(os.path.realpath(__file__))
    f = open(os.path.join(here, pfi_txt), 'r')
    list_reqs = []
    for line in f.readlines():
        list_reqs.append(line.replace('\n', ''))
    return list_reqs

if sys.version_info[:2] < (2, 7):
    tests_requires.append('unittest2')

if sys.version_info[:2] <= (3, 3):
    tests_requires.append('mock')

setup(
    name='phabricator',
    version='0.7.0',
    author='Disqus',
    author_email='opensource@disqus.com',
    url='http://github.com/disqus/python-phabricator',
    description='Phabricator API Bindings',
    packages=find_packages(),
    zip_safe=False,
    test_suite='tests.test_phabricator',
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
