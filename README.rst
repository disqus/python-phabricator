python-phabricator
==================

Installation
------------

::

	$ python setup.py install

Usage
-----

Use the API by instantiating it, and then calling the method through dotted notation chaining::

	from phabricator import Phabricator
	phab = Phabricator()  # This will use your ~/.arcrc file
	phab.user.whoami()

Parameters are passed as keyword arguments to the resource call::

    phab.user.find(aliases=["sugarc0de"])

Documentation on all methods is located at https://secure.phabricator.com/conduit/

Updating interfaces.json
------------------------

Copy ``gen_api_interfaces.php`` to  ``scripts/util`` of your Phabricator installation and run it::

    $ ./gen_api_interfaces.php > interfaces.json
