python-phabricator
==================

.. image:: https://travis-ci.org/MediaMiser/python-phabricator.png?branch=master
	:target: https://travis-ci.org/MediaMiser/python-phabricator

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

Interface out-of-date
---------------------

If Phabricator modifies Conduit and the included ``interfaces.json`` is out-of-date or to make sure
to always have the latest interfaces::

        from phabricator import Phabricator
        phab = Phabricator()
        phab.update_interfaces()
        phab.user.whoami()
