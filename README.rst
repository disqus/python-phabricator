python-phabricator
~~~~~~~~~~~~~~~~~~

Install the API bindings:

	python setup.py install

Use the API by instantiating it, and then calling the method through dotted notation chaining::

	from phabricator import Phabricator
	phab = Phabricator()  # This will use your ~/.arcrc file
	phab.user.whoami()

Parameters are passed as keyword arguments to the resource call::

    phab.user.find(aliases=["sugarc0de"])

Documentation on all methods is located at https://secure.phabricator.com/conduit/
