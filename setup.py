#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='phabricator',
    version='0.4.1',
    author='DISQUS',
    author_email='opensource@disqus.com',
    url='http://github.com/disqus/python-phabricator',
    description='Phabricator API Bindings',
    packages=find_packages(),
    zip_safe=False,
    test_suite='nose.collector',
    install_requires=['future'],
    tests_require=['nose', 'unittest2', 'mock'],
    include_package_data=True,
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
