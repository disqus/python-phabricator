[![PyPI version](https://badge.fury.io/py/phabricator.svg)](https://badge.fury.io/py/phabricator)
[![Build Status](https://travis-ci.org/disqus/python-phabricator.png?branch=master)](https://travis-ci.org/disqus/python-phabricator)
[![coverage](https://github.com/SebastianoF/python-phabricator/blob/master/coverage.svg)](https://github.com/SebastianoF/python-phabricator/blob/master/coverage.svg)

# python-phabricator

## Installation
```
$ pip install phabricator
```

## Usage

Use the API by instantiating it, and then calling the method through dotted notation chaining::
```
from phabricator import Phabricator
phab = Phabricator()  # This will use your ~/.arcrc file
phab.user.whoami()
```
You can also use::
```
phab = Phabricator(host='https://my-phabricator.org/api/', token='api-mytoken')
```
Parameters are passed as keyword arguments to the resource call::
```
phab.user.find(aliases=["sugarc0de"])
```
Documentation on all methods is located at https://secure.phabricator.com/conduit/

## Development

To run the testing, check the coverage and re-create the local coverage badge 
first install:
```
pip install pytest-cov
pip install coverage
pip install coverage-badge
```
followed by:
```
pytest --cov --cov-report html
coverage html
open htmlcov/index.html  # optional to visualise the coverage
coverage-badge -f -o coverage.svg  # optional to update the coverage badge
```

## Interface out-of-date

If Phabricator modifies Conduit and the included ``interfaces.json`` is out-of-date or to make sure
to always have the latest interfaces::
```
from phabricator import Phabricator
phab = Phabricator()
phab.update_interfaces()
phab.user.whoami()
```