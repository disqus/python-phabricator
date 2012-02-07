"""
python-phabricator
------------------
>>> api = phabricator.Phabricator()
>>> api.user.whoami().userName
'example'

For more endpoints, see https://secure.phabricator.com/conduit/

"""
try:
    __version__ = __import__('pkg_resources') \
        .get_distribution('phabricator').version
except:
    __version__ = 'unknown'

import hashlib
import httplib
import json
import os.path
import socket
import time
import urllib
import urlparse

__all__ = ['Phabricator']

# Default phabricator interfaces
INTERFACES = json.loads(open(os.path.join(os.path.dirname(__file__), 'interfaces.json'), 'r').read())

# Load ~/.arcrc if it exists
try:
    ARCRC = json.loads(open(os.path.join(os.path.expanduser('~'), '.arcrc'), 'r').read())
except IOError:
    ARCRC = None

class InterfaceNotDefined(NotImplementedError): pass
class APIError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return '%s: %s' % (self.code, self.message)

class InvalidAccessToken(APIError): pass

class Result(object):
    def __init__(self, response):
        self.response = response

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, repr(self.response))

    def __iter__(self):
        for r in self.response:
            yield r

    def __getitem__(self, key):
        return self.response[key]

    def __getattr__(self, key):
        return self.response[key]

    def __len__(self):
        return len(self.response.keys())

    def keys(self):
        return self.response.keys()

class Resource(object):
    RESPONSE_SHIELD = 'for(;;);'

    def __init__(self, api, interface=INTERFACES, endpoint=None, method=None):
        self.api = api
        self.interface = interface
        self.endpoint = endpoint
        self.method = method

    def __getattr__(self, attr):
        if attr in getattr(self, '__dict__'):
            return getattr(self, attr)
        interface = self.interface
        if attr not in interface:
            interface[attr] = {}
        return Resource(self.api, interface[attr], attr, self.endpoint)

    def __call__(self, **kwargs):
        return self._request(**kwargs)

    def _request(self, **kwargs):
        # Check for missing variables
        resource = self.interface

        def validate_kwarg(key, target):
            # Always allow list
            if isinstance(key, list):
                return all([validate_kwarg(x, target[0]) for x in key])
            return type(key).__name__ == target

        for k in resource.get('required', []):
            if k not in [ x.split(':')[0] for x in kwargs.keys() ]:
                raise ValueError('Missing required argument: %s' % k)
            if isinstance(kwargs.get(k), list) and not isinstance(resource['required'][k], list):
                raise ValueError('Wrong argument type: %s is not a list' % k)
            elif not validate_kwarg(kwargs.get(k), resource['required'][k]):
                if isinstance(resource['required'][k], list):
                    raise ValueError('Wrong arguemnt type: %s is not a list of %ss' % (k, resource['required'][k][0]))
                raise ValueError('Wrong arguemnt type: %s is not a %s' % (k, resource['required'][k]) )

        conduit = self.api.conduit

        if conduit:
            # Already authenticated, add session key to json data
            kwargs['__conduit__'] = conduit
        elif self.method == 'conduit' and self.endpoint == 'connect':
            # Not authenticated, requesting new session key
            token = str(int(time.time()))
            kwargs['authToken'] = token
            kwargs['authSignature'] = self.api.generate_hash(token)
        else:
            # Authorization is required, silently auth the user
            self.api.connect()
            kwargs['__conduit__'] = self.api.conduit

        url = urlparse.urlparse(self.api.host)
        if url.scheme == 'https':
            conn = httplib.HTTPSConnection(url.netloc, timeout=self.api.timeout)
        else:
            conn = httplib.HTTPConnection(url.netloc, timeout=self.api.timeout)

        path = url.path + '%s.%s' % (self.method, self.endpoint)

        headers = {
            'User-Agent': 'python-phabricator/%s' % str(self.api.clientVersion),
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        body = urllib.urlencode({
            "params": json.dumps(kwargs),
            "output": self.api.response_format
        })

        # TODO: Use HTTP "method" from interfaces.json
        conn.request('POST', path, body, headers)
        response = conn.getresponse()
        data = self._parse_response(response.read())

        return Result(data['result'])

    def _parse_response(self, data):
        # Check for response shield
        if not data.startswith(self.RESPONSE_SHIELD):
            raise APIError('', 'Conduit returned an invalid response')

        # Remove repsonse shield
        if data.startswith(self.RESPONSE_SHIELD):
            data = data[len(self.RESPONSE_SHIELD):]

        # Process the response back to python
        parsed = self.api.formats[self.api.response_format](data)

        # Errors return 200, so check response content for exception
        if parsed['error_code']:
            raise APIError(parsed['error_code'], parsed['error_info'])

        return parsed


class Phabricator(Resource):
    formats = {
        'json': lambda x: json.loads(x),
    }

    def __init__(self, username=None, certificate=None, host=None,
            timeout=5, response_format='json', **kwargs):

        # Set values in ~/.arcrc as defaults
        if ARCRC:
            self.host = host if host else ARCRC['hosts'].keys()[0]
            self.username = username if username else ARCRC['hosts'][self.host]['user']
            self.certificate = certificate if certificate else ARCRC['hosts'][self.host]['cert']
        else:
            self.host = host
            self.username = username
            self.certificate = certificate

        self.timeout = timeout
        self.response_format = response_format
        self.client = 'python-phabricator'
        self.clientVersion = 1
        self.clientDescription = socket.gethostname() + ':python-phabricator'
        self.conduit = None

        super(Phabricator, self).__init__(self)

    def _request(self, **kwargs):
        raise SyntaxError('You cannot call the Conduit API without a resource.')

    def connect(self):
        auth = Resource(api=self, method='conduit', endpoint='connect')

        response = auth(user=self.username, host=self.host,
                client=self.client, clientVersion=self.clientVersion)

        self.conduit = {
            'sessionKey': response.sessionKey,
            'connectionID': response.connectionID
        }

    def generate_hash(self, token):
        return hashlib.sha1(token + self.api.certificate).hexdigest()

